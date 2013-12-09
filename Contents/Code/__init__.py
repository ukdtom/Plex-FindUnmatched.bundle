####################################################################################################
#	This plugin will find unmatched items for Plex Media Server
#
#	Made by dane22....A Plex Community member
#	Contributions by s_razer
#
#	Original python code was made by a Plex community member named whymse
#	and can be found here: 
#	http://forums.plexapp.com/index.php/topic/39712-list-unmatched-media/?p=252267
#	
#	The original idea to the code belongs to whymse
#
#	I just made it a little bit more user friendly
#
####################################################################################################

import os
import unicodedata
import string
import urllib
import time

VERSION = ' V0.0.1.16'
NAME = 'FindUnmatched'
ART = 'art-default.jpg'
ICON = 'icon-FindUnmatched.png'
PREFIX = '/applications/findUnmatched'

myPathList = {}			# Contains dict of section keys and file-path
files = []				# Contains list of detected medias from the filesystem of a section
myMediaPaths = []		# Contains filepath of selected section medias from the database
myResults = []			# Contains the end results
bScanStatus = 0			# Current status of the background scan
initialTimeOut = 10		# When starting a scan, how long in seconds to wait before displaying a status page. Needs to be at least 1.

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

####################################################################################################
# Main menu
####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
@route(PREFIX + '/MainMenu')
def MainMenu(random=0):
	Log.Debug("**********  Starting MainMenu  **********")
	oc = ObjectContainer()
	#Use global variables due to my lack of Python skills....SNIFF...
	global myPathList

	# Clear the myPathList
	myPathList.clear
	try:
		sections = XML.ElementFromURL(PMS_URL).xpath('//Directory')
		for section in sections:
			sectiontype = section.get('type')
			if sectiontype != "photo":
				title = section.get('title')
				key = section.get('key')
				paths = section.xpath('Location/@path')
				Log.Debug("Title of section is %s with a key of %s and a path of : %s" %(title, key, paths))
				myPathList[key]= ', '.join(paths)
				oc.add(DirectoryObject(key=Callback(backgroundScan, title=title, sectiontype=sectiontype, key=key, random=time.clock()), title='Look in section "' + title + '"', summary='Look for unmatched files in "' + title + '"'))
	except:
		Log.Critical("Exception happened in MainMenu")
	oc.add(PrefsObject(title='Preferences', thumb=R('icon-prefs.png')))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc

####################################################################################################
# Scan Filesystem for a section
####################################################################################################
@route(PREFIX + '/scanFiles')
def scanFiles(title, key, sectiontype):
	Log.Debug("*******  Starting scanFiles  ***********")
	global myPathList
	global files
	global bScanStatus

	try:
		files[:] = []
		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = PMS_URL + key + "/all"
		# Now we need all filepaths added to the section
		for myKey in myPathList.keys():
			if key == myKey:
				myPaths = myPathList[key].split(', ')
				for myPath in myPaths:
					files.append(listTree(myPath))
		Log.Debug("********  Files found are the following: ***************")
		Log.Debug(files)
		# Check for no files
		if len(files[0]) == 0:
			bScanStatus = 90
			Log.Debug("*******  scanFiles: no files found ***********")
	except:
		Log.Critical("Exception happened in scanFiles")
		bScanStatus = 99
		raise
	Log.Debug("*******  Ending scanFiles  ***********")
	return

####################################################################################################
# Find missing files
####################################################################################################
@route(PREFIX + '/compare')
def compare(title):
	Log.Debug("*******  Starting compare  ***********")
	global myMediaPaths
	global files
	global bScanStatus
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
	oc2 = ObjectContainer(title1=title, no_cache=True)
	global myResults
	counter = 1
	for item in myResults:
		title=item.decode('utf-8','ignore')
                title2=title
                if title[0] == '[':
			title = title[1:]
		if title[len(title)-1] == ']':
			title = title[:-1]
		title = str(counter) + ": " + title
		counter += 1
		oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title=title, summary="Unmatched file: \n\n"+title2))

	# Reset the scanner status
	bScanStatus = 0
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
	global bScanStatusCount
	myResults[:] = []
	Log.Debug("******* Start findUnmatchedFiles ******")
	Log.Debug("*********************** Database paths: *******************************************")
	Log.Debug(myMediaPaths)
	Log.Debug("*********************** FileSystem Paths: *****************************************")
	files = str(files)[2:-2].replace("'", "").split(', ')
	Log.Debug(files)
	for filePath in files:
		Log.Debug("Handling file #%s: %s" %(bScanStatusCount, filePath.decode("utf-8")))
		bScanStatusCount += 1
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
	global bScanStatusCount
	Log.Debug("******* Starting ListTree with a path of %s***********" %(top))
	r = files[:]
	try:
		if not os.path.exists(top):
			Log.Debug("The file share [%s] is not mounted" %(top))
			return r
		for f in os.listdir(top):
			pathname = os.path.join(top, f)
			Log.Debug("Found file #%s named: %s" %(bScanStatusCount, pathname))
			if os.path.isdir(pathname):
				r = listTree(pathname, r)
			elif os.path.isfile(pathname):
				bScanStatusCount += 1
				filename = urllib.unquote(pathname).decode('utf8')
				composed_filename = unicodedata.normalize('NFKC', filename)
				filename = urllib.quote(composed_filename.encode('utf8'))
				r.append(filename)
			else:
				Log.Debug("Skipping %s" %(pathname))
		return r
	except UnicodeDecodeError:
		Log.Critical("Detected an invalid caracter in the file/directory following this : %s" %(pathname))
	except:
		Log.Critical("Detected an exception in listTree")
		bScanStatus = 99
		raise

####################################################################################################
# This function will scan a movie section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanMovieDB')
def scanMovieDB(myMediaURL):
	Log.Debug("******* Starting scanMovieDB with an URL of %s***********" %(myMediaURL))
	global myMediaPaths
	global bScanStatusCount
	global bScanStatusCountOf
	bScanStatusCount = 0
	bScanStatusCountOf = 0
	myMediaPaths[:] = []
	myTmpPath = []
	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Video')
		bScanStatusCountOf = len(myMedias)
		for myMedia in myMedias:
			title = myMedia.get('title')			
			myTmpPaths = (',,,'.join(myMedia.xpath('Media/Part/@file')).split(',,,'))
			for myTmpPath in myTmpPaths:
				filename = urllib.unquote(myTmpPath).decode('utf8')
				composed_filename = unicodedata.normalize('NFKC', filename)
				myFilePath = urllib.quote(composed_filename.encode('utf8'))
				# Remove esc backslash if present and on Windows
				if Platform.OS == "Windows":
					myFilePath = myFilePath.replace(':%5C%5C', ':%5C')
				bScanStatusCount += 1
				Log.Debug("Media #%s from database: '%s' with a path of : %s" %(bScanStatusCount, title, myFilePath))
				myMediaPaths.append(myFilePath)
	except:
		Log.Critical("Detected an exception in scanMovieDB")
		bScanStatus = 99
		raise
	Log.Debug("******* Ending scanMovieDB ***********")

####################################################################################################
# This function will scan a TV-Show section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanShowDB')
def scanShowDB(myMediaURL):
	Log.Debug("******* Starting scanShowDB with an URL of %s***********" %(myMediaURL))
	global bScanStatusCount
	global bScanStatusCountOf
	global myMediaPaths
	global myMedias
	myMediaPaths[:] = []
	bScanStatusCount = 0

	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Directory')
		bScanStatusCountOf = len(myMedias)
		for myMedia in myMedias:
			bScanStatusCount += 1
			ratingKey = myMedia.get("ratingKey")
			myURL = "http://" + host + "/library/metadata/" + ratingKey + "/allLeaves"
			Log.Debug("Show %s of %s with a RatingKey of %s at myURL: %s" %(bScanStatusCount, bScanStatusCountOf, ratingKey, myURL))
			myMedias2 = XML.ElementFromURL(myURL).xpath('//Video')
			for myMedia2 in myMedias2:
				title = myMedia2.get("grandparentTitle") + "/" + myMedia2.get("title")
				# Using three commas as one has issues with some filenames.
				myFilePath = (',,,'.join(myMedia2.xpath('Media/Part/@file')).split(',,,'))
				for myFilePath2 in myFilePath:
					filename = urllib.unquote(myFilePath2).decode('utf8')
					composed_filename = unicodedata.normalize('NFKC', filename)
					myFilePath2 = urllib.quote(composed_filename.encode('utf8'))
					# Remove esc backslash if present and on Windows
					# The Colon prevents breaking Windows file shares.
					if Platform.OS == "Windows":
						myFilePath2 = myFilePath2.replace(':%5C%5C', ':%5C')
					myMediaPaths.append(myFilePath2)
					Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath2))
	except:
		Log.Critical("Detected an exception in scanShowDB")
		bScanStatus = 99
		raise # Dumps the error so you can see what the problem is
	Log.Debug("******* Ending scanShowDB ***********")

####################################################################################################
# This function will scan a Music section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanArtistDB')
def scanArtistDB(myMediaURL):
	Log.Debug("******* Starting scanArtistDB with an URL of %s***********" %(myMediaURL))
	global bScanStatusCount
	global bScanStatusCountOf
	global myMediaPaths
	myMediaPaths[:] = []
	try:
		myMedias = XML.ElementFromURL(myMediaURL).xpath('//Directory')
		bScanStatusCountOf = len(myMedias)
		for myMedia in myMedias:
			bScanStatusCount += 1
			ratingKey = myMedia.get("ratingKey")
			myURL = "http://" + host + "/library/metadata/" + ratingKey + "/allLeaves"
			Log.Debug("%s of %s with a RatingKey of %s at myURL: %s" %(bScanStatusCount, bScanStatusCountOf, ratingKey, myURL))
			myMedias2 = XML.ElementFromURL(myURL).xpath('//Track')
			for myMedia2 in myMedias2:
				title = myMedia2.get("grandparentTitle") + "/" + myMedia2.get("title")
				# This returns a double backslash for every backslash
				#myFilePath = str(myMedia2.xpath('Media/Part/@file'))[2:-2]
				# This appears to work fine
				myFilePath = ',,,'.join(myMedia2.xpath('Media/Part/@file'))
				filename = urllib.unquote(myFilePath).decode('utf8')
				composed_filename = unicodedata.normalize('NFKC', filename)
				myFilePath = urllib.quote(composed_filename.encode('utf8'))
				# Remove esc backslash if present and on Windows
				if Platform.OS == "Windows":
					myFilePath = myFilePath.replace(':%5C%5C', ':%5C')
				myMediaPaths.append(myFilePath)
				Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath))
	except:
		Log.Critical("Detected an exception in scanArtistDB")
		bScanStatus = 99
		raise
	Log.Debug("******* Ending scanArtistDB ***********")

####################################################################################################
# Start the scanner in a background thread and provide status while running
####################################################################################################
@route(PREFIX + '/backgroundScan')
def backgroundScan(title, key, sectiontype, refreshCount=0, random=0):
	Log.Debug("******* Starting backgroundScan *********")
	# Current status of the Background Scanner:
	# 0=not running, 1=db, 2=filesystem, 3=compare, 4=complete, 
	# Errors: 90=filesystem empty, 99=Other Error
	global bScanStatus
	# Current status count (ex. "Show 2 of 31")
	global bScanStatusCount
	global bScanStatusCountOf
	# The webclient won't reload if the url is the same for some reason, so I put in a refresh counter
	# to give a different url every time.
	refreshCount = int(refreshCount)
	refreshCount += 1
	try:
		if bScanStatus == 0:
			bScanStatusCount = 0
			bScanStatusCountOf = 0
			# Start scanner
			Thread.Create(backgroundScanThread, globalize=True, title=title, key=key, sectiontype=sectiontype)
			# Wait 10 seconds unless the scanner finishes
			x = 0
			while (x <= initialTimeOut):
				time.sleep(1)
				x += 1
				if bScanStatus == 4:
					Log.Debug("************** Scan Done, stopping wait **************")
					break
				if bScanStatus >= 90:
					Log.Debug("************** Error in thread, stopping wait **************")
					break
		# Summary to add to the status
		summary = "The Plex client will only wait a few seconds for us to work, so we run it in the background. This requires you to keep checking on the status until it is complete. \n\n"
		if bScanStatus == 1:
			# Scanning Database
			summary = summary + "The Database is being scanned. \nScanning " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf) + ". \nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Scanning Database " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf) + ".", no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="Scanning the database. Check Status.", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="Scanning " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf), summary=summary))
			return oc2
		elif bScanStatus == 2:
			# Scanning Filesystem
			summary = summary + "The filesystem is being scanned. \n Scanning file #" + str(bScanStatusCount) + ".\nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Scanning Filesystem #" + str(bScanStatusCount), no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="Scanning filesystem. Check Status", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="Scanning file #" + str(bScanStatusCount), summary=summary))
		elif bScanStatus == 3:
			# Comparing results
			summary = summary + "Comparing the results. \n Scanning #" + str(bScanStatusCount) + ".\nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Comparing #" + str(bScanStatusCount), no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="Comparing the results. Check Status", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="File #" + str(bScanStatusCount), summary=summary))
		elif bScanStatus == 4:
			# See Results
			summary = "Scan complete, click here to get the results."
			oc2 = ObjectContainer(title1="Results", no_history=True)
			oc2.add(DirectoryObject(key=Callback(compare, title=title), title="*** Get the Results. ***", summary=summary))
		elif bScanStatus == 90:
			# scanFiles returned no files
			summary = "The filesystem scan returned no files."
			oc2 = ObjectContainer(title1="Results", no_history=True)
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="*** The filesystem is empty. ***", summary=summary))
			bScanStatus = 0
		elif bScanStatus == 99:
			# Error condition set by scanner
			summary = "An internal error has occurred. Please check the logs"
			oc2 = ObjectContainer(title1="Internal Error Detected. Please check the logs",no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="An internal error has occurred.", summary=summary))
			bScanStatus = 0
		else:
			# Unknown status. Should not happen.
			summary = "Something went horribly wrong. The scanner returned an unknown status."
			oc2 = ObjectContainer(title1="Uh Oh!.", no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, refreshCount=refreshCount, title=title, sectiontype=sectiontype, key=key), title="*** Unknown status from scanner ***", summary=summary))
	except:
		Log.Critical("Detected an exception in backgroundScan")
		raise
	Log.Debug("******* Ending backgroundScan ***********")
	return oc2


####################################################################################################
# Background scanner thread.
####################################################################################################
@route(PREFIX + '/backgroundScanThread')
def backgroundScanThread(title, key, sectiontype):
	Log.Debug("*******  Starting backgroundScanThread  ***********")
	global myMediaPaths
	global myPathList
	global bScanStatus
	global bScanStatusCount
	global bScanStatusCountOf
	
	try:
		bScanStatus = 1
		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = PMS_URL + key + "/all"		
		Log.Debug("Path to medias in section is %s" %(myMediaURL))

		# Scan the database based on the type of section
		if sectiontype == "movie":
			scanMovieDB(myMediaURL)
		if sectiontype == "artist":
			scanArtistDB(myMediaURL)
		if sectiontype == "show":
			scanShowDB(myMediaURL)
			Log.Debug("**********  Section filepath as stored in the database are: %s  *************" %(myMediaPaths))
		# Stop scanner on error
		if bScanStatus >= 90: return

		# Scan the filesystem
		bScanStatus = 2
		bScanStatusCount = 0
		scanFiles(title=title, sectiontype=sectiontype, key=key)
		# Stop scanner on error
		if bScanStatus >= 90: return

		# Find unmatched files
		bScanStatus = 3
		bScanStatusCount = 0
		findUnmatchedFiles()
		# Stop scanner on error
		if bScanStatus >= 90: return

		# Allow status menu to give give the results
		bScanStatus = 4

	except:
		Log.Critical("Exception happened in backgroundScanThread")
		bScanStatus = 99
		raise
	Log.Debug("*******  Ending backgroundScanThread  ***********")
