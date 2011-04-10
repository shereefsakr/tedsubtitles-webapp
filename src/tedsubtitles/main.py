"""
tedsubtitles is a appengine web site to download TED Talk Translations in SRT format
Copyright (C) 2011  Shereef Sakr

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import cgi
import os

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import images

import sys
import urlparse
import re
from django.utils import simplejson as json
import urllib2

class TEDSubtitleLang :
    def __init__ (self):
        self.code = ''
        self.name = ''
        
    def __repr__ (self):
        return ( self.code + ':' + self.name )

# Format Time from TED Subtitles format to SRT time Format
def formatTime ( time ) :
    milliseconds = 0
    seconds = ((time / 1000) % 60)
    minutes = ((time / 1000) / 60)
    hours = (((time / 1000) / 60) / 60)
    
    milliseconds = str ( milliseconds )
    if ( len ( milliseconds ) < 2 ) :
        milliseconds = '0' + milliseconds
    seconds = str ( seconds )
    if ( len ( seconds ) < 2 ) :
        seconds = '0' + seconds
    minutes = str (minutes)
    if ( len ( minutes ) < 2 ) :
        minutes = '0' + minutes
    hours = str ( hours )
    if ( len ( hours ) < 2 ) :
        hours = '0' + hours
    
    formatedTime = hours + ':' + minutes + ':' + seconds + ',' + milliseconds
    return formatedTime

# Convert TED Subtitles to SRT Subtitles
def convertTEDSubtitlesToSRTSubtitles ( jsonString , introDuration ) :
    jsonObject = json.loads( jsonString )

    srtContent = ''
    captionIndex = 1

    for caption in jsonObject['captions'] :
        startTime = str ( formatTime ( introDuration + caption['startTime'] ) )
        endTime = str ( formatTime ( introDuration + caption['startTime'] + caption['duration'] ) )

        srtContent += ( str ( captionIndex ) + '\n' )
        srtContent += ( startTime + ' --> ' + endTime + '\n' )
        srtContent += ( caption['content'] + '\n' )
        srtContent += '\n'

        captionIndex = captionIndex + 1
    return srtContent

def getTEDSubtitlesByTalkID ( talkId , language ) :
    tedSubtitleUrl = 'http://www.ted.com/talks/subtitles/id/' + str(talkId) + '/lang/' + language
    req = urllib2.Request(tedSubtitleUrl)
    response = urllib2.urlopen(req)
    result = response.read()
    return ( result )

def getTEDSubtitlesLangsByURL ( tedtalkUrl ) :
    req = urllib2.Request(tedtalkUrl)
    response = urllib2.urlopen(req)
    result = response.read()
    
    langs = []
    
    langSplits = result.split ( '%7B%22LanguageCode%22%3A%22' )
    langSplits = langSplits[1:]
    
    for langEntry in langSplits :
        langSplit = langEntry.split ( '%22%2C%22Name%22%3A%22' )
        subtitleLang = TEDSubtitleLang ()
        subtitleLang.code = langSplit[0]
        subtitleLang.name = langSplit[1].split ( '%' )[0]
        
        langs.append(subtitleLang)
    
    return ( langs )

def getTEDSubtitlesByURL ( tedtalkUrl , language ) :
    req = urllib2.Request(tedtalkUrl)
    response = urllib2.urlopen(req)
    result = response.read()
    
    ## Get Talk ID value
    splits = result.split ( ';ti=' )
    talkId = splits[1].split ( '&' )[0]
    #print talkId
    
    ## Get Talk Intro Duration value
    splits = result.split ( ';introDuration=' )
    talkIntroDuration = splits[1].split ( '&' )[0]
    talkIntroDuration = int ( talkIntroDuration )
    #print talkIntroDuration
    
    jsonString = getTEDSubtitlesByTalkID ( talkId , language )
    
    srtContent = convertTEDSubtitlesToSRTSubtitles ( jsonString , talkIntroDuration )
    return ( srtContent )

class MainPage(webapp.RequestHandler):
    def get(self):
        template_values = {}

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class GetSubtitlesPage (webapp.RequestHandler):
    def get(self):
        tedtalkUrl = self.request.get ( 'tedurl' )
        language = self.request.get ( 'langcode' )
        
        srtContent = getTEDSubtitlesByURL ( tedtalkUrl , language )
        
        # Generate SRT file name
        splits = tedtalkUrl.split ( '/' )
        srtFilename = splits[len ( splits )-1].split ('.')[0]

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.headers['Content-Disposition'] = 'attachment;filename=' + srtFilename + '.srt'
        self.response.out.write( srtContent )

class GetAvailableLanguagesPage (webapp.RequestHandler):
    def get(self):
        tedtalkUrl = ''
        error = ''
        langs = {}
        
        tedtalkUrl = self.request.get ( 'tedurl' )
        
        if not re.match( "^http://", tedtalkUrl, re.IGNORECASE) :
            tedtalkUrl = "http://" + tedtalkUrl
        
        if not re.match( "^http://www.ted.com/", tedtalkUrl, re.IGNORECASE) :
            error = 'URL is not valid'
        
        try :
            parsedUrl = urlparse.urlparse(tedtalkUrl)
        
            tedtalkUrl = parsedUrl.geturl()
        except:
            error = "URL is not valid test"
        
        if ( not error ) :
            langs = getTEDSubtitlesLangsByURL ( tedtalkUrl )
        
        template_values = { 'tedurl' : tedtalkUrl
                           , 'langs' : langs
                           , 'error' : error }
        
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication(
                                     [('/', MainPage ),
                                      ('/getavailablelanguages', GetAvailableLanguagesPage) ,
                                      ('/getsubtitles', GetSubtitlesPage)] ,
                                    debug=True)
#####
#"""
def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
#"""

## Test Main function
"""
langs = getTEDSubtitlesLangsByURL ( 'http://www.ted.com/talks/richard_st_john_s_8_secrets_of_success.html' )

for lang in langs :
    print repr ( lang )
#"""