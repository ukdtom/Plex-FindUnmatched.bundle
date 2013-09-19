####################################################################################################
#	This plugin will find unmatched items for Plex Media Server
#
#	Made by dane22....A Plex Community member
#
#	Original python code was made by a Plex community member named macr0t0r
#	and can be found here: 
#	http://forums.plexapp.com/index.php/topic/39712-list-unmatched-media/?p=252267
#	
#	The intelectual rights to the code belongs to macr0t0r
#
#	I just made it a little bit more user friendly
#
####################################################################################################

import os
import unicodedata
import string

NAME = 'FindUnmatched'
ART = 'art-default.jpg'
ICON = 'icon-FindUnmatched.png'
PREFIX = '/applications/findUnmatched'

####################################################################################################
# Start function
####################################################################################################
def Start():
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME
	ObjectContainer.view_group = 'List'
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = 0
	getPrefs()

####################################################################################################
# Main menu
####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
def MainMenu():
	Log.Debug("**********  Starting MainMenu  **********")
	oc = ObjectContainer(no_cache=True)	
	try:
		sections = XML.ElementFromURL(PMS_URL).xpath('//Directory')	
		for section in sections:			
			title = section.get('title')
			key = section.get('key')
			paths = section.xpath('Location/@path')
			Log.Debug("Title of section is %s with a key of %s and a path of : %s" %(title, key, paths))	
			oc.add(DirectoryObject(key=Callback(confirmScan, title=title, paths=paths, key=key), title='Look in section "' + title + '"'))		
	except:
		pass
	oc.add(PrefsObject(title='Preferences', thumb=R('icon-prefs.png')))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# Grab user selection of a section, and get to work
####################################################################################################
@route(PREFIX + '/confirmScan')
def confirmScan(title, paths, key):
	Log.Debug("*******  Starting confirmScan  ***********")
	oc = ObjectContainer(title2="Search")
	myMediaURL = PMS_URL + key + "/all"		
	myMediaPaths = []
	Log.Debug("Path to medias in section is %s" %(myMediaURL))
	# Scan the database
	myMediaPaths = scanDB(myMediaURL)
	# Scan the filesystem
	files = listTree(paths)
	missing = findUnmatchedFiles(files, myMediaPaths)
	Log.Info("*********************** The END RESULT Start *****************")
	Log.Info(missing)
	Log.Info("*********************** The END RESULT End *****************")
	Log.Debug("*******  Ending confirmScan  ***********")
	return oc

####################################################################################################
# Do the files
####################################################################################################
@route(PREFIX + '/findUnmatchedFiles')
def findUnmatchedFiles(filePaths, dbPaths):
	missing = []
	fname = ""
	display_ignores = False

	Log.Debug("******* Start findUnmatchedFiles ******")
	Log.Debug("***********************************************************************************")
	Log.Debug("Database paths:")
	Log.Debug(dbPaths)
	Log.Debug("***********************************************************************************")
	Log.Debug("File paths:")
	Log.Debug(filePaths)
	missing.append("The following files are missing in the Plex database")        
        for filePath in filePaths:
		Log.Debug("Handling file %s ..." %(filePath))		
		if filePath not in dbPaths:
			myext = os.path.splitext(filePath)[1].lower()
			cext = myext.rstrip("']")
			fname = os.path.split(filePath)[1]
			Log.Debug("filepath was not in paths, so fname is now %s" %(fname))
			Log.Debug("file ext is : %s" %(cext))
			if (fname in OK_FILES):
				#Don't do anything for acceptable files
				Log.Debug("File is part of OK_Files")
				continue
			elif (cext in OTHER_EXTENSIONS):
				#ignore images and subtitles
				Log.Debug("File is part of ignored extentions")
				continue
			elif (cext not in VIDEO_EXTENSIONS):
				#these shouldn't be here
				if (display_ignores):
					Log.Debug("Ignoring %s" %(filePath))
					continue
			else:
				Log.Debug("Missing this file")
				missing.append(filePath)
	return missing

####################################################################################################
# Get user settings, and if not existing, get the defaults
####################################################################################################
@route(PREFIX + '/getPrefs')
def getPrefs():
	Log.Debug("*********  Starting to get User Prefs  ***************")
	host = Prefs['host']
	if host.find(':') == -1:
		host += ':32400'
	global PMS_URL
	PMS_URL = 'http://%s/library/sections/' %(host)
	Log.Debug("PMS_URL is : %s" %(PMS_URL))
	global VIDEO_EXTENSIONS
	VIDEO_EXTENSIONS = Prefs['VIDEO_EXTENSIONS']
	Log.Debug("VIDEO_EXTENSIONS from prefs are : %s" %(VIDEO_EXTENSIONS))	
	global OK_FILES
	OK_FILES = Prefs['OK_FILES']
	Log.Debug("OK_FILES from prefs are : %s" %(OK_FILES))
	global IGNORED_DIRS
	IGNORED_DIRS = Prefs['IGNORED_DIRS']
	Log.Debug("IGNORED_DIRS from prefs are : %s" %(IGNORED_DIRS))
	global OTHER_EXTENSIONS
	OTHER_EXTENSIONS = Prefs['OTHER_EXTENSIONS']
	Log.Debug("OTHER_EXTENSIONS from prefs are : %s" %(OTHER_EXTENSIONS))
	Log.Debug("*********  Ending get User Prefs  ***************")
	return

####################################################################################################
# This function will scan the filesystem for files
####################################################################################################
@route(PREFIX + '/listTree')
def listTree(top, files=list()):
	Log.Debug("******* Starting ListTree with a path of %s***********" %(top))
	r = files[:]
	try:
		if not os.path.exists(top):
			Log.Debug("The file share [%s] is not mounted" %(top))
			return r
		for f in os.listdir(top):
			pathname = os.path.join(top, f)
			Log.Debug("Found a pathname named : %s" %(pathname))
			if os.path.isdir(pathname):
				r = listTree(pathname, r)
			elif os.path.isfile(pathname):
#				r.append(unicodedata.normalize('NFC', pathname))
				r.append(pathname)
			else:
				Log.Debug("Skipping %s" %(pathname))
		return r
	except UnicodeDecodeError:
		Log.Critical("Detected an invalid caracter in the file/directory following this : %s" %(pathname))

####################################################################################################
# This function will scan a section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanDB')
def scanDB(myMediaURL, myMediaPaths=list()):
	Log.Debug("******* Starting scanDB with an URL of %s***********" %(myMediaURL))
	r = myMediaPaths[:]
	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Video')
		for myMedia in myMedias:
			title = myMedia.get('title')
			myFilePath = str(myMedia.xpath('Media/Part/@file'))[2:-2]
			myMediaPaths.append(myFilePath)
			Log.Debug("Media: '%s' with a path of : %s" %(title, myFilePath))
			r.append(myFilePath)
		return r
	except:
		Log.Critical("Detected an exception in scanDB")
		pass

