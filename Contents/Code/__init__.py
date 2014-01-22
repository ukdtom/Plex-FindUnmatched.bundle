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
import fnmatch
import io
import itertools

VERSION = ' V0.0.1.22'
NAME = 'FindUnmatched'
ART = 'art-default.jpg'
ICON = 'icon-FindUnmatched.png'
PREFIX = '/applications/findUnmatched'

myPathList = {}			# Contains dict of section keys and file-path
myResults = []			# Contains the end results
bScanStatus = 0			# Current status of the background scan
initialTimeOut = 10		# When starting a scan, how long in seconds to wait before displaying a status page. Needs to be at least 1.

# These are no longer defined globally
#files = []				# Contains list of detected medias from the filesystem of a section
#myMediaPaths = []		# Contains filepath of selected section medias from the database

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
# Called by the framework every time a user changes the prefs
####################################################################################################
@route(PREFIX + '/ValidatePrefs')
def ValidatePrefs():
	# If the old setting from v0.0.1.20 and before that allowed scanning all extensions, then update to the new setting.
	if Prefs['VALID_EXTENSIONS'].lower() == 'all': 
		Log.Debug("VALID_EXTENSIONS=all, setting ALL_EXTENSIONS to True and resetting VALID_EXTENSIONS")
		SendHTTP('http://' + Prefs['host'] + '/:/plugins/com.plexapp.plugins.findUnmatch/prefs/' + 'set?VALID_EXTENSIONS=')
		SendHTTP('http://' + Prefs['host'] + '/:/plugins/com.plexapp.plugins.findUnmatch/prefs/' + 'set?ALL_EXTENSIONS=True')
	# Do we need to reset the extentions?
	if Prefs['RESET_EXTENTIONS']:
		ResetExtensions()

####################################################################################################
# Reset the Media Extentions to the defaults
####################################################################################################
@route(PREFIX + '/ResetExtensions')
def ResetExtensions():
	Log.Debug("Resetting Extensions in Preferences.")
	myHTTPPrefix = 'http://' + Prefs['host'] + '/:/plugins/com.plexapp.plugins.findUnmatch/prefs/'
	myURL = myHTTPPrefix + 'set?RESET_EXTENTIONS=False'
	Log.Debug('Prefs Sending : ' + myURL)
	SendHTTP(myURL)
	myURL = myHTTPPrefix + 'set?VALID_EXTENSIONS='
	Log.Debug('Prefs Sending : ' + myURL)
	SendHTTP(myURL)
	myURL = myHTTPPrefix + 'set?IGNORED_FILES='
	Log.Debug('Prefs Sending : ' + myURL)
	SendHTTP(myURL)
	myURL = myHTTPPrefix + 'set?IGNORED_DIRS='
	Log.Debug('Prefs Sending : ' + myURL)
	SendHTTP(myURL)
	myURL = myHTTPPrefix + 'set?IGNORED_EXTENSIONS='
	Log.Debug('Prefs Sending : ' + myURL)
	SendHTTP(myURL)

####################################################################################################
# Send an http request to the PMS
####################################################################################################
@route(PREFIX + '/SendHTTP')
def SendHTTP(myURL):
	u = urllib.urlopen(myURL)

####################################################################################################
# Scan Filesystem for a section
####################################################################################################
@route(PREFIX + '/scanFiles')
def scanFiles(title, key, sectiontype):
	Log.Debug("*******  Starting scanFiles  ***********")
	global myPathList
	global bScanStatus
	files = []

	try:
		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = PMS_URL + key + "/all"
		# Now we need all filepaths added to the section
		for myKey in myPathList.keys():
			if key == myKey:
				myPaths = myPathList[key].split(', ')
				for myPath in myPaths:
					files.extend(listTree(myPath))
		Log.Debug("********  Files found are the following: ***************")
		Log.Debug(files)
		# Check for no files
		if files == '':
			bScanStatus = 90
			Log.Debug("*******  scanFiles: no files found: files='' ***********")
		elif len(files[0]) == 0:
			bScanStatus = 90
			Log.Debug("*******  scanFiles: no files found: len(files[0])=0 ***********")
		return files
	except:
		Log.Critical("Exception happened in scanFiles")
		bScanStatus = 99
		raise
	Log.Debug("*******  Ending scanFiles  ***********")

####################################################################################################
# This function will scan the filesystem for files
####################################################################################################
@route(PREFIX + '/listTree')
def listTree(top, files=list(), plexignore=[]):
	global bScanStatusCount
	Log.Debug("******* Starting ListTree with a path of %s***********" %(top))
	r = files[:]
	# If the directory is in the ignore list don't process it.
	if os.path.basename(os.path.normpath(top)) in IGNORED_DIRS:
		Log.Debug("Ignoring directory %s" %(top))
		return r
	try:
		if not os.path.exists(top):
			Log.Debug("The file share [%s] is not mounted" %(top))
			return r
		# If enabled, read in .plexignore if it exists
		if enablePlexignore:
			if os.path.exists(top + '/.plexignore'):
				Log.Debug("Found .plexignore in: %s" %(top))
				plexignore.append(readPlexignore(top + '/.plexignore'))
			else:
				# If there is no .plexignore then add empty list to plexignore stack
				plexignore.append([])
			# Collapse plexignore into one table with itertools.chain.from_iterable()
			# and remove duplicates with set() and convert back to list with list()
			plexignoreList = list(set(itertools.chain.from_iterable(plexignore)))
			Log.Debug("plexignoreList is: %s" %(plexignoreList))
		
		for f in os.listdir(top):
			pathname = os.path.join(top, f)
			Log.Debug("Found file #%s named: %s" %(bScanStatusCount, pathname))
			# If the pathname is a dir, scan into it
			if os.path.isdir(pathname):
				r = listTree(pathname, r, plexignore)
				if enablePlexignore: Log.Debug("plexignoreList is: %s" %(plexignoreList))
			elif os.path.isfile(pathname):
				bScanStatusCount += 1
				
				#################################
				# Look to see if the file has a match in plexignoreList
				caught=0
				if enablePlexignore:
					for ignore in plexignoreList:
						if fnmatch.fnmatch(pathname, "*" + ignore + "*"):
							Log.Debug("Ignoring %s because it matches %s from .plexignore" %(pathname, ignore))
							caught=1
							break
				if caught == 1: continue
				
				#################################
				
				filename = urllib.unquote(pathname).decode('utf8')
				composed_filename = unicodedata.normalize('NFKC', filename)
				filename = urllib.quote(composed_filename.encode('utf8'))
				r.append(filename)
			else:
				Log.Debug("Skipping %s" %(pathname))
		
		# Remove last item in plexignore, then reset plexignoreList
		if enablePlexignore: plexignore.pop(); plexignoreList = list(set(itertools.chain.from_iterable(plexignore)))
		return r
	except UnicodeDecodeError:
		Log.Critical("Detected an invalid caracter in the file/directory following this : %s" %(pathname))
	except:
		Log.Critical("Detected an exception in listTree")
		bScanStatus = 99
		raise

####################################################################################################
# This function will read and format a givin .plexignore file
####################################################################################################
def readPlexignore(file):
	Log.Debug("*******  Starting readPlexignore  ***********")
	plexignore=[]

	# Open and read .plexignore file
	f = io.open(file); 	fileIn = f.readlines(); f.close
	for line in fileIn:
		line = line.strip()
		# Ignore comment line
		if line[:1] == '#': pass
		# Ignore blank line
		elif line == '': pass
		# Add line
		else: plexignore.append(line)
	Log.Debug(".plexignore contains: %s" %(plexignore))
	Log.Debug("*******  Ending readPlexignore  ***********")
	return plexignore

####################################################################################################
# Display the results.
####################################################################################################
@route(PREFIX + '/results')
def results(title):
	Log.Debug("*******  Starting results  ***********")
	global bScanStatus
	global myResults

	Log.Info("*********************** The END RESULT Start *****************")
	Log.Info("****** Found %d Items missing **************" %(len(myResults)))
	Log.Info("The following files are missing in Plex database from section named: %s:" %(title))
	if len(myResults) == 0:
		myResults.append("All is good....no files are missing")
	Log.Info(myResults)
	Log.Info("*********************** The END RESULT End *****************")
	foundNo = len(myResults)
	if foundNo == 1:
		if "All is good....no files are missing" in myResults:
			foundNo = 0
	title = ("%d Unmatched Items found" %(foundNo))
	oc2 = ObjectContainer(title1=title, no_cache=True)
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
	Log.Debug("*******  Ending results  ***********")
	return oc2

####################################################################################################
# Look for found files in the database.
####################################################################################################
@route(PREFIX + '/findUnmatchedFiles')
def findUnmatchedFiles(files, myMediaPaths):
	fname = ""
	display_ignores = False
	global myResults
	global bScanStatusCount
	myResults = []

	Log.Debug("******* Start findUnmatchedFiles ******")

	# Convert IGNORED_FILES to a list. Replace gets rid of any space after the comma
	ignoredFilesList= IGNORED_FILES.replace(', ',',').split(',')

	Log.Debug("*********************** Database paths: *******************************************")
	Log.Debug(myMediaPaths)
	Log.Debug("*********************** FileSystem Paths: *****************************************")
	files = str(files)[2:-2].replace("'", "").split(', ')
	Log.Debug(files)
	for filePath in files:
		# Decode filePath 
		filePath2 = urllib.unquote(filePath).decode('utf8')
		Log.Debug("Handling file #%s: %s" %(bScanStatusCount, filePath2))
		bScanStatusCount += 1
		# If the file is not in the database, figure out what to do.
		if filePath not in myMediaPaths:
			myext = os.path.splitext(filePath)[1].lower()
			cext = myext.rstrip("']")
			fname = os.path.split(filePath2)[1].lower()

			if (fname in IGNORED_FILES.lower()):
				# Filename is in ignored files, won't catch wildcards
				Log.Debug("File is part of ignored files.")
				continue
			elif (cext in IGNORED_EXTENSIONS.lower()):
				# File extension in in ignored extensions
				Log.Debug("File is part of ignored extentions")
				continue
			elif (cext not in VALID_EXTENSIONS.lower() and VALID_EXTENSIONS.lower() != 'all' and not ALL_EXTENSIONS):
				# If file extension is not in VALID_EXTENSIONS and VALID_EXTENSIONS != 'all', then ignoe the file and ALL_EXTENSIONS is not True
				# Keeping "VALID_EXTENSIONS.lower() != 'all'" for backwards compatibility for prefs from v0.0.1.20 and before - Chris
				if (display_ignores):
					Log.Debug("Ignoring %s" %(filePath2))
					continue
			else:
				###############################################
				# Search the ignoredFilesList for a match against the current file.
				# Needed for wildcards. Ugly but it works.
				caught=0
				for l in ignoredFilesList:
					if fnmatch.fnmatch(fname, l):
						Log.Debug("File matched %s in the ignored files list" %(l))
						caught=1
						break
				###############################################
				if caught == 1:
					continue
				else:
					Log.Debug("Missing this file")
					myResults.append(urllib.unquote(filePath))
	return myResults

####################################################################################################
# Get user settings, and if not existing, get the defaults
####################################################################################################
@route(PREFIX + '/getPrefs')
def getPrefs():
	Log.Debug("*********  Starting to get User Prefs  ***************")
	if Prefs['VALID_EXTENSIONS'].lower() == 'all': ValidatePrefs()
	global host
	host = Prefs['host']
	if host.find(':') == -1:
		host += ':32400'
	global PMS_URL
	PMS_URL = 'http://%s/library/sections/' %(host)
	Log.Debug("PMS_URL is : %s" %(PMS_URL))
	global ALL_EXTENSIONS
	ALL_EXTENSIONS = Prefs['ALL_EXTENSIONS']
	Log.Debug("ALL_EXTENSIONS is : %s" %(ALL_EXTENSIONS))
	global VALID_EXTENSIONS
	VALID_EXTENSIONS = Prefs['VALID_EXTENSIONS']
	Log.Debug("VALID_EXTENSIONS from prefs are : %s" %(VALID_EXTENSIONS))
	global IGNORED_FILES
	IGNORED_FILES = Prefs['IGNORED_FILES']
	Log.Debug("IGNORED_FILES from prefs are : %s" %(IGNORED_FILES))
	global IGNORED_DIRS
	IGNORED_DIRS = Prefs['IGNORED_DIRS']
	Log.Debug("IGNORED_DIRS from prefs are : %s" %(IGNORED_DIRS))
	global IGNORED_EXTENSIONS
	IGNORED_EXTENSIONS = Prefs['IGNORED_EXTENSIONS']
	Log.Debug("IGNORED_EXTENSIONS from prefs are : %s" %(IGNORED_EXTENSIONS))
	global enablePlexignore
	enablePlexignore = Prefs['ENABLE_PLEXIGNORE']
	Log.Debug("ENABLE_PLEXIGNORE is : %s" %(enablePlexignore))
	Log.Debug("*********  Ending get User Prefs  ***************")
	return

####################################################################################################
# This function will scan a movie section for filepaths in medias
####################################################################################################
@route(PREFIX + '/scanMovieDB')
def scanMovieDB(myMediaURL):
	Log.Debug("******* Starting scanMovieDB with an URL of %s***********" %(myMediaURL))
	global bScanStatusCount
	global bScanStatusCountOf
	bScanStatusCount = 0
	bScanStatusCountOf = 0
	myMediaPaths = []
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
		return myMediaPaths
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
	myMediaPaths = []
	bScanStatusCount = 0
	filecount = 0

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
					filecount += 1
					Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath2))
		return (myMediaPaths, filecount)
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
	myMediaPaths = []
	filecount = 0
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
				filecount += 1
				Log.Debug("Media from database: '%s' with a path of : %s" %(title, myFilePath))
		return (myMediaPaths, filecount)
	except:
		Log.Critical("Detected an exception in scanArtistDB")
		bScanStatus = 99
		raise
	Log.Debug("******* Ending scanArtistDB ***********")

####################################################################################################
# Start the scanner in a background thread and provide status while running
####################################################################################################
@route(PREFIX + '/backgroundScan')
def backgroundScan(title, key, sectiontype, random=0):
	Log.Debug("******* Starting backgroundScan *********")
	# Current status of the Background Scanner:
	# 0=not running, 1=db, 2=filesystem, 3=compare, 4=complete
	# Errors: 90=filesystem empty, 99=Other Error
	global bScanStatus
	# Current status count (ex. "Show 2 of 31")
	global bScanStatusCount
	global bScanStatusCountOf
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
					oc2 = results(title=title)
					return oc2
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
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), title=title, sectiontype=sectiontype, key=key), title="Scanning the database. Check Status.", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), title=title, sectiontype=sectiontype, key=key), title="Scanning " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf), summary=summary))
			return oc2
		elif bScanStatus == 2:
			# Scanning Filesystem
			summary = summary + "The filesystem is being scanned. \n Scanning file #" + str(bScanStatusCount) + " of about " + str(bScanStatusCountOf) + ".\nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Scanning Filesystem #" + str(bScanStatusCount) + " of about " + str(bScanStatusCountOf) + ".", no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), title=title, sectiontype=sectiontype, key=key), title="Scanning filesystem. Check Status", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), title=title, sectiontype=sectiontype, key=key), title="Scanning file #" + str(bScanStatusCount), summary=summary))
		elif bScanStatus == 3:
			# Comparing results
			summary = summary + "Comparing the results. \n Scanning #" + str(bScanStatusCount) + ".\nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Comparing #" + str(bScanStatusCount), no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), title=title, sectiontype=sectiontype, key=key), title="Comparing the results. Check Status", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), title=title, sectiontype=sectiontype, key=key), title="File #" + str(bScanStatusCount), summary=summary))
		elif bScanStatus == 4:
			# See Results
			summary = "Scan complete, click here to get the results."
			oc2 = ObjectContainer(title1="Results", no_history=True)
			oc2.add(DirectoryObject(key=Callback(results, title=title), title="*** Get the Results. ***", summary=summary))
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
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="An internal error has occurred.", summary=summary))
			bScanStatus = 0
		else:
			# Unknown status. Should not happen.
			summary = "Something went horribly wrong. The scanner returned an unknown status."
			oc2 = ObjectContainer(title1="Uh Oh!.", no_history=True)
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="*** Unknown status from scanner ***", summary=summary))
			bScanStatus = 0
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
	global bScanStatus
	global bScanStatusCount
	global bScanStatusCountOf
	
	try:
		bScanStatus = 1
		# Make sure we have the latest Prefs
		getPrefs()

		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = PMS_URL + key + "/all"
		Log.Debug("Path to medias in section is %s" %(myMediaURL))

		# Scan the database based on the type of section
		if sectiontype == "movie":
			myMediaPaths = scanMovieDB(myMediaURL)
			filecount = bScanStatusCount
		if sectiontype == "artist":
			myMediaPaths, filecount = scanArtistDB(myMediaURL)
		if sectiontype == "show":
			myMediaPaths, filecount = scanShowDB(myMediaURL)
		Log.Debug("**********  Section filepath as stored in the database are: %s  *************" %(myMediaPaths))
		# Stop scanner on error
		if bScanStatus >= 90: return

		# Scan the filesystem
		bScanStatus = 2
		bScanStatusCount = 0
		bScanStatusCountOf = filecount
		files = scanFiles(title, key, sectiontype)
		# Stop scanner on error
		if bScanStatus >= 90: return

		# Find unmatched files
		bScanStatus = 3
		bScanStatusCount = 0
		findUnmatchedFiles(files=files, myMediaPaths=myMediaPaths)
		# Stop scanner on error
		if bScanStatus >= 90: return

		# Allow status menu to give give the results
		bScanStatus = 4

	except:
		Log.Critical("Exception happened in backgroundScanThread")
		bScanStatus = 99
		raise
	Log.Debug("*******  Ending backgroundScanThread  ***********")
