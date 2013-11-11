import xbmcplugin
import xbmcgui
import sys
import urllib, urllib2, urlparse
import re
import json

import httplib
from pyamf import AMF0, AMF3

from pyamf import remoting
from pyamf.remoting.client import RemotingService

thisPlugin = int(sys.argv[1])
baseLink = "http://www.dmax.de"
urlShows = baseLink + "/programme/"
urlShowsSub = baseLink + "/wp-content/plugins/dni_plugin_core/ajax.php?action=dni_listing_items_filter&letter=%s&id=0e0&post_id=17268"

rootLink = "http://www.dmax.de"
height = 1080;#268|356|360|400|572|576
const = "ef59d16acbb13614346264dfe58844284718fb7b"
playerID = 586587148001;
publisherID = 1659832546;
playerKey = "AAAAAGLvCOI~,a0C3h1Jh3aQKs2UcRZrrxyrjE0VH93xl"

_regex_extractShowsLetter = re.compile("<a href=\"#id=0e0&letter=([A-Z#])\" "); 
_regex_extractShows = re.compile("href=\"(.*?)\".*?src=\"(.*?)\" alt=\"(.*?)\"",re.DOTALL);
_regex_extractEpisode = re.compile("<a class=\"dni-episode-browser-item pagetype-(video)\" href=\"(.*?)\">.*?<p>(.*?)</p>.*?</a>", re.DOTALL);

_regex_extractVideoIds = re.compile("<li data-number=\"[0-9]*\" data-guid=\"([0-9]*)\"");
_regex_extractVideoIdsSingleVideo = re.compile("<param name=\"@videoPlayer\" value=\"(.*?)\" />");

def mainPage():
    global thisPlugin
    page = load_page(urlShows)
    for letterItem in _regex_extractShowsLetter.finditer(page):
        letter = letterItem.group(1)
        link  = (urlShowsSub) % (letter)
        addDirectoryItem(letter, {"action" : "letter", "link": link}) 
    xbmcplugin.endOfDirectory(thisPlugin)

def showLetter(link):
    page = load_page(link)
    jsonShows = json.loads(page)
    pageCount = jsonShows['total_pages']
    for i in range(1, pageCount+1):
        urlShowsPage = link+"&page=%i" % i
        page = load_page(urlShowsPage)
        jsonShowsPage = json.loads(page)
        for show in _regex_extractShows.finditer(jsonShowsPage['html']):
            show_title = show.group(3);
            show_link = show.group(1) + "episoden/"
            show_img = show.group(2)
            addDirectoryItem(show_title, {"action" : "show", "link": show_link}, show_img) 
    xbmcplugin.endOfDirectory(thisPlugin)

def showPage(link):
    global thisPlugin
    page = load_page(link)
    
    _regex_extractSeasonsInfo = re.compile("<section class=\"cfct-module dni-episode-browser-items-container\" id=\".*?\" data-module-id=\"(.*?)\" data-post-id=\"(.*?)\">(.*?)</select>",re.DOTALL)
    _regex_extractSeasons = re.compile("<option value=\"(.*?)\">(.*?)</option>")
    season_link_base = "http://www.dmax.de/wp-content/plugins/dni_plugin_core/ajax.php?action=dni_episode_browser_get_season&post=%s&module=%s&season=%s";
    seasonsInfo = _regex_extractSeasonsInfo.search(page)
    data_module_id = seasonsInfo.group(1)
    data_post_id = seasonsInfo.group(2)
    seasonsSelect = seasonsInfo.group(3)
    for  season in _regex_extractSeasons.finditer(seasonsSelect):
        season_link = season_link_base % (data_post_id,data_module_id,season.group(1))
        addDirectoryItem(season.group(2), {"action" : "season", "link": season_link})
    xbmcplugin.endOfDirectory(thisPlugin)

def showPageSeason(link):
    page = load_page(link)
    
    episodes = list(_regex_extractEpisode.finditer(page))
    
    _regex_episodeTitles = re.compile("<h3.*?>(.*?)</h3>")
    _regex_episodeImg = re.compile("src=\"(.*?)\" alt=\"(.*?)\"")
    
    for episode in episodes:
        episod_title = ""
        for title in _regex_episodeTitles.finditer(episode.group(0)):
            episod_title += title.group(1) + " "
        episode_link =episode.group(2)
        
        episode_img_item = _regex_episodeImg.search(episode.group(0))
        episode_img = ""
        if episode_img_item is not None:
            episode_img = episode_img_item.group(1)
        addDirectoryItem(episod_title, {"action" : "episode", "link": episode_link}, episode_img, isFolder=False)
    xbmcplugin.endOfDirectory(thisPlugin)

def showEpisode(link):
    page = load_page(link)
    
    videoIds = list(_regex_extractVideoIds.finditer(page));
    
    if len(videoIds) == 0:
         videoIds = list(_regex_extractVideoIdsSingleVideo.finditer(page));

    
    playlistContent = []
    x = 0
    for videoId in videoIds:
        video = play(const, playerID, videoId.group(1), publisherID);
        playlistContent.append(video)
        x = x + 1
        
    playPlaylist(link, playlistContent)
    
def load_page(url):
    print "Load: " + url
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    link = response.read()
    response.close()
    return link

def addDirectoryItem(name, parameters={}, pic="", isFolder=True):
    li = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=pic)
    #if not isFolder:
    #    li.setProperty('IsPlayable', 'true')
    url = sys.argv[0] + '?' + urllib.urlencode(parameters)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=isFolder)

def build_amf_request(const, playerID, videoPlayer, publisherID):
    env = remoting.Envelope(amfVersion=3)
    env.bodies.append(
        (
            "/1",
            remoting.Request(
                target="com.brightcove.player.runtime.PlayerMediaFacade.findMediaById",
                body=[const, playerID, videoPlayer, publisherID],
                envelope=env
            )
        )
    )
    return env

def get_clip_info(const, playerID, videoPlayer, publisherID):
    conn = httplib.HTTPConnection("c.brightcove.com")
    envelope = build_amf_request(const, playerID, videoPlayer, publisherID)
    conn.request("POST", "/services/messagebroker/amf?playerKey=" + playerKey, str(remoting.encode(envelope).read()), {'content-type': 'application/x-amf'})
    response = conn.getresponse().read()
    response = remoting.decode(response).bodies[0][1].body
    return response  

def play(const, playerID, videoPlayer, publisherID):
    rtmpdata = get_clip_info(const, playerID, videoPlayer, publisherID)
    streamName = ""
    default = 'skip'
    streamUrl = rtmpdata.get('FLVFullLengthURL', default);
    
    for item in sorted(rtmpdata['renditions'], key=lambda item:item['frameHeight'], reverse=False):
        streamHeight = item['frameHeight']
        
        if streamHeight <= height:
            streamUrl = item['defaultURL']
    
    streamName = streamName + rtmpdata['displayName']
    return [streamName, streamUrl];

def playPlaylistOff(playlistLink, playlistContent):    
    global thisPlugin
    playlist = "stack://";
    for i in range(len(playlistContent)):
        playlist += playlistContent[i][1];
        if(i!=len(playlistContent)-1):
            playlist += " , ";

    listitem = xbmcgui.ListItem(path=playlist)
    return xbmcplugin.setResolvedUrl(thisPlugin, True, listitem)

def playPlaylist(playlistLink, playlistContent):    
    player = xbmc.Player();
    
    playerItem = xbmcgui.ListItem(playlistLink);
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO);
    playlist.clear();
    print "playPlaylist";
    
    for link in playlistContent:
        listItem = xbmcgui.ListItem(link[0]);
        listItem.setProperty("PlayPath", link[1]);
        listItem.addStreamInfo('video',{})
        playlist.add(url=link[1], listitem=listItem);
    
    player.play(playlist, playerItem)
    xbmc.sleep(300) #Wait for Player to open
    if player.pause():
        player.play() #Start playing

def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
                                
        return param

if not sys.argv[2]:
    mainPage()
else:
    params = get_params()
    print params['action']
    if params['action'] == "show":
        showPage(urllib.unquote(params['link']))
    elif params['action'] == "season":
        showPageSeason(urllib.unquote(params['link']))
    elif params['action'] == "episode":
        showEpisode(urllib.unquote(params['link']))
    elif params['action'] == "letter":
        showLetter(urllib.unquote(params['link']))
    else:
        mainPage()
