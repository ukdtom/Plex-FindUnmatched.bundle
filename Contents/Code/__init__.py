####################################################################################################
#	This plugin will find unmatched items for Plex Media Server
#
#	Made by dane22....A Plex Community member
#
#	Original python code was made by a Plex community member named whymse
#	and can be found here: 
#	http://forums.plexapp.com/index.php/topic/39712-list-unmatched-media/?p=252267
#	
#	The origen idea to the code belongs to whymse
#
#	I just made it a little bit more user friendly
#
####################################################################################################

import os
import unicodedata
import string
import urllib

VERSION = ' V0.0.1.9'
NAME = 'FindUnmatched'
ART = 'art-default.jpg'
ICON = 'icon-FindUnmatched.png'
PREFIX = '/applications/findUnmatched'

myPathList = {}			# Contains dict of section keys and file-path
files = []			# Contains list of detected medias from the filesystem of a section
myMediaPaths = []		# Contains filepath of selected section medias from the database
myResults = []			# Contains the end results

####################################################################################################
# Start function
####################################################################################################
def Start():
	print("********  Started %s on %s  **********" %(NAME  + VERSION, Platform.OS))
	Log.Debug("*******  Started %s on %s  ***********" %(NAME  + VERSION, Platform.OS))
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME  + VERSION
	ObjectContainer.view_group = 'List'
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = 0
	getPrefs()
	print("Remember check dual path for section")


####################################################################################################
# Main menu
####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
@route(PREFIX + '/MainMenu')
def MainMenu():
	Log.Debug("**********  Starting MainMenu  **********")
	oc = ObjectContainer(no_cache=True)
	#Use global variables due to my lack of Python skills....SNIFF...
	global myPathList
	# Clear the myPathList
	myPathList.clear
	try:
		sections = XML.ElementFromURL(PMS_URL).xpath('//Directory')
		for section in sections:
			title = section.get('title')
			key = section.get('key')
			sectiontype = section.get('type')
			paths = section.xpath('Location/@path')
			Log.Debug("Title of section is %s with a key of %s and a path of : %s" %(title, key, paths))
			for path in paths:
				# Need to append the key and path to a global variable, in order to avoid a bug in Plex API
				myPathList[key]=path
			oc.add(DirectoryObject(key=Callback(scanDB, title=title, sectiontype=sectiontype, key=key), title='Look in section "' + title + '"'))	
	except:
		Log.Critical("Exception happend in MainMenu")
		pass
	oc.add(PrefsObject(title='Preferences', thumb=R('icon-prefs.png')))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# Grab user selection of a section, and scan the database
####################################################################################################
@route(PREFIX + '/scanDB')
def scanDB(title, key, sectiontype):
	Log.Debug("*******  Starting scanDB  ***********")
	global myMediaPaths
	global myPathList
	try:
		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = PMS_URL + key + "/all"		
		Log.Debug("Path to medias in section is %s" %(myMediaURL))
		# Scan the database based on the type of section
		if sectiontype == "movie":
			scanMovieDB(myMediaURL)
		if sectiontype == "show":
			scanShowDB(myMediaURL)
		if sectiontype == "artist":
			scanArtistDB(myMediaURL)
		Log.Debug("**********  Section filepath as stored in the database are: %s  *************" %(myMediaPaths))	
		oc2 = ObjectContainer(title1="Database scanned", mixed_parents=True)
		oc2.add(DirectoryObject(key=Callback(scanFiles, title=title, sectiontype=sectiontype, key=key), title="****** Click here to scan the file-system ******"))
	except:
		Log.Critical("Exception happend in scanDB")
		pass
	return oc2

####################################################################################################
# Scan Filesystem for a section
####################################################################################################
@route(PREFIX + '/scanFiles')
def scanFiles(title, key, sectiontype):
	Log.Debug("*******  Starting scanFiles  ***********")	
	global myPathList
	global files
	try:
		files[:] = []
		Log.Debug("Section type is %s" %(sectiontype))
		oc = ObjectContainer(title2="Search FileSystem")
		myMediaURL = PMS_URL + key + "/all"		
		# Now we need all filepaths added to the section
		for myKey in myPathList.keys():
			if key == myKey:
				files.append(listTree(myPathList[key]))
		Log.Debug("********  Files found are the following: ***************")
		Log.Debug(files)
		oc2 = ObjectContainer(title1="FileSystem scanned", mixed_parents=True)
		oc2.add(DirectoryObject(key=Callback(compare, title=title), title="****** Click here to compare ******"))
	except:
		Log.Critical("Exception happend in scanDB")
		pass
	return oc2

####################################################################################################
# Find missing files
####################################################################################################
@route(PREFIX + '/compare')
def compare(title):
	Log.Debug("*******  Starting compare  ***********")
	global myMediaPaths
	global files
	findUnmatchedFiles()
	Log.Info("*********************** The END RESULT Start *****************")
	Log.Info("****** Found %d Items missing **************" %(len(myResults)))
	Log.Info("The following files are missing in Plex database from section named: %s:" %(title))
	if len(myResults) == 0:
		myResults.append("All is good....no files are missing")
	Log.Info(myResults)
	Log.Info("*********************** The END RESULT End *****************")
	Log.Debug("*******  Ending confirmScan  ***********")
	foundNo = len(myResults)
	if foundNo == 1:
		if "All is good....no files are missing" in myResults:
			foundNo = 0	
	title = ("%d Unmatched Items found" %(foundNo))
	oc2 = ObjectContainer(title1=title, mixed_parents=True)
	global myResults
	for item in myResults:
		oc2.add(DirectoryObject(key=Callback(MainMenu), title=item.decode('utf-8','ignore')))
	return oc2

####################################################################################################
# Do the files
####################################################################################################
@route(PREFIX + '/findUnmatchedFiles')
def findUnmatchedFiles():
	fname = ""
	display_ignores = False

	global files
	global myMediaPaths
	global myResults

	myResults[:] = []

	Log.Debug("******* Start findUnmatchedFiles ******")
	Log.Debug("*********************** Database paths: *******************************************")
	Log.Debug(myMediaPaths)
	Log.Debug("*********************** FileSystem Paths: *****************************************")
	files = str(files)[2:-2].replace("'", "").split(', ')
	Log.Debug(files)
	for filePath in files:
		Log.Debug("Handling file %s" %filePath.decode("utf-8"))
		if filePath not in myMediaPaths:
			myext = os.path.splitext(filePath)[1].lower()
			cext = myext.rstrip("']")
			fname = os.path.split(filePath)[1]
			if (fname in OK_FILES):
				#Don't do anything for acceptable files
				Log.Debug("File is part of OK_Files")
				continue
			elif (cext in OTHER_EXTENSIONS):
				#ignore images and subtitles
				Log.Debug("File is part of ignored extentions")
				continue
			elif (cext not in VALID_EXTENSIONS):
				#these shouldn't be here
				if (display_ignores):
					Log.Debug("Ignoring %s" %(filePath))
					continue
			else:
				Log.Debug("Missing this file")
				myResults.append(urllib.unquote(filePath))

	return 

####################################################################################################
# Get user settings, and if not existing, get the defaults
####################################################################################################
@route(PREFIX + '/getPrefs')
def getPrefs():
	Log.Debug("*********  Starting to get User Prefs  ***************")
	global host
	host = Prefs['host']
	if host.find(':') == -1:
		host += ':32400'
	global PMS_URL
	PMS_URL = 'http://%s/library/sections/' %(host)
	Log.Debug("PMS_URL is : %s" %(PMS_URL))
	global VALID_EXTENSIONS
	VALID_EXTENSIONS = Prefs['VALID_EXTENSIONS']
	Log.Debug("VALID_EXTENSIONS from prefs are : %s" %(VALID_EXTENSIONS))	
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
			Log.Debug("Found a file named : %s" %(pathname))
			if os.path.isdir(pathname):
				r = listTree(pathname, r)
			elif os.path.isfile(pathname):
				r.append(urllib.quote(pathname.encode('utf8')))					
			else:
				Log.Debug("Skipping %s" %(pathname))
		return r
	except UnicodeDecodeError:
		Log.Critical("Detected an invalid caracter in the file/directory following this : %s" %(pathname))

####################################################################################################
# This function will scan a movie section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanMovieDB')
def scanMovieDB(myMediaURL):
	Log.Debug("******* Starting scanMovieDB with an URL of %s***********" %(myMediaURL))
	global myMediaPaths
	myMediaPaths[:] = []
	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Video')
		for myMedia in myMedias:
			title = myMedia.get('title')
			myFilePath = str(myMedia.xpath('Media/Part/@file'))[2:-2]
			myFilePath = urllib.quote(myFilePath).replace('%25', '%')	
			# Remove esc backslash if present and on Windows
			if Platform.OS == "Windows":
				myFilePath = myFilePath.replace('%5C%5C', '%5C')
			myMediaPaths.append(myFilePath)
			Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath))
			myMediaPaths.append(myFilePath)
		return
	except:
		Log.Critical("Detected an exception in scanMovieDB")
		pass

####################################################################################################
# This function will scan a TV-Show section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanShowDB')
def scanShowDB(myMediaURL):
	Log.Debug("******* Starting scanShowDB with an URL of %s***********" %(myMediaURL))
	global myMediaPaths
	myMediaPaths[:] = []
	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Directory')
		for myMedia in myMedias:
			ratingKey = myMedia.get("ratingKey")
			Log.Debug("RatingKey is %s" %(ratingKey))
			myURL = "http://" + host + "/library/metadata/" + ratingKey + "/allLeaves"
			Log.Debug("myURL is %s" %(myURL))
			myMedias2 = XML.ElementFromURL(myURL).xpath('//Video')
			for myMedia2 in myMedias2:
				title = myMedia2.get("grandparentTitle") + "/" + myMedia2.get("title")
				myFilePath = myMedia2.xpath('Media/Part/@file')
				for myFilePath2 in myFilePath:
					myFilePath2 = urllib.quote(myFilePath2).replace('%25', '%')
					# Remove esc backslash if present and on Windows
					if Platform.OS == "Windows":
						myFilePath2 = myFilePath2.replace('%5C%5C', '%5C')
					myMediaPaths.append(myFilePath2)					
					Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath2))
		return
	except:
		Log.Critical("Detected an exception in scanShowDB")
		pass
	Log.Debug("******* Ending scanShowDB ***********")


####################################################################################################
# This function will scan a Music section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanArtistDB')
def scanArtistDB(myMediaURL):
	Log.Debug("******* Starting scanArtistDB with an URL of %s***********" %(myMediaURL))
	global myMediaPaths
	myMediaPaths[:] = []
	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Directory')
		for myMedia in myMedias:
			ratingKey = myMedia.get("ratingKey")
			Log.Debug("RatingKey is %s" %(ratingKey))
			myURL = "http://" + host + "/library/metadata/" + ratingKey + "/allLeaves"
			Log.Debug("myURL is %s" %(myURL))
			myMedias2 = XML.ElementFromURL(myURL).xpath('//Track')
			for myMedia2 in myMedias2:
				title = myMedia2.get("grandparentTitle") + "/" + myMedia2.get("title")
				myFilePath = str(myMedia2.xpath('Media/Part/@file'))[2:-2]
				myFilePath2 = urllib.quote(myFilePath).replace('%25', '%')
				# Remove esc backslash if present and on Windows
				if Platform.OS == "Windows":
					myFilePath2 = myFilePath2.replace('%5C%5C', '%5C')
				myMediaPaths.append(myFilePath2)
				Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath2))
		return
	except:
		Log.Critical("Detected an exception in scanArtistDB")
		pass
	Log.Debug("******* Ending scanArtistDB ***********")


