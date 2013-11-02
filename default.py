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
_regex_extractEpisode = re.compile("<a class=\"dni-episode-browser-item pagetype-video\" href=\"(.*?)\">.*?src=\"(.*?)\" alt=\"(.*?)\".*?<p>(.*?)</p>.*?</a>", re.DOTALL);
_regex_extractVideoIds = re.compile("<li data-number=\"[0-9]*\" data-guid=\"([0-9]*)\"");

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
    
    episodes = list(_regex_extractEpisode.finditer(page))
    
    for episode in episodes:
        episod_title = episode.group(3)
        episode_link =episode.group(1)
        episode_img = episode.group(2)
        addDirectoryItem(episod_title, {"action" : "episode", "link": episode_link}, episode_img)
    xbmcplugin.endOfDirectory(thisPlugin)

def showEpisode(link):
    page = load_page(link)
    
    videoIds = list(_regex_extractVideoIds.finditer(page));
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

def addDirectoryItem(name, parameters={}, pic=""):
    li = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=pic)
    url = sys.argv[0] + '?' + urllib.urlencode(parameters)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)

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

def playPlaylist(playlistLink, playlistContent):
    player = xbmc.Player();
    
    playerItem = xbmcgui.ListItem(playlistLink);
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO);
    playlist.clear();
    print "playPlaylist";
    
    for link in playlistContent:
        listItem = xbmcgui.ListItem(link[0]);
        listItem.setProperty("PlayPath", link[1]);
        playlist.add(url=link[1], listitem=listItem);
    
    player.play(playlist, playerItem);

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
    elif params['action'] == "episode":
        showEpisode(urllib.unquote(params['link']))
    elif params['action'] == "letter":
        showLetter(urllib.unquote(params['link']))
    else:
        mainPage()
