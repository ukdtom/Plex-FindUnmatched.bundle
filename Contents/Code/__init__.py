####################################################################################################
#	This plugin will find unmatched items for Plex Media Server
#
#	Made by dane22....A Plex Community member
#	Contributions by srazer
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


VERSION = ' V1.0.0.3'
NAME = 'FindUnmatched'
ART = 'art-default.jpg'
ICON = 'icon-FindUnmatched.png'

PREFIX = '/applications/findUnmatched'
MYHEADER = {}
APPGUID = '7608cf36-742b-11e4-8b39-00089b13a0b2'
DESCRIPTION = 'Find medias missed by Plex scanners'

myResults = []			# Contains the end results
bScanStatus = 0			# Current status of the background scan
initialTimeOut = 10		# When starting a scan, how long in seconds to wait before displaying a status page. Needs to be at least 1.
display_ignores = True	# When True, files that are ignored will be put in the log

####################################################################################################
# Start function
####################################################################################################
def Start():
#	print("********  Started %s on %s  **********" %(NAME  + VERSION, Platform.OS))
	Log.Debug("*******  Started %s on %s  ***********" %(NAME  + VERSION, Platform.OS))
	global MYHEADER
	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = NAME  + VERSION
	ObjectContainer.view_group = 'List'
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = 0
	getToken()
	ValidatePrefs()
	logPrefs()

#********** Get token from plex.tv *********
''' This will return a valid token, that can be used for authenticating if needed, to be inserted into the header '''
# DO NOT APPEND THE TOKEN TO THE URL...IT MIGHT BE LOGGED....INSERT INTO THE HEADER INSTEAD
@route(PREFIX + '/getToken')
def getToken():
	Log.Debug('Starting to get the token')
	if Prefs['Authenticate']:
		# Start by checking, if we already got a token
		if 'authentication_token' in Dict and Dict['authentication_token'] != 'NuKeMe':
			Log.Debug('Got a token from local storage')
			global MYHEADER
			MYHEADER['X-Plex-Token'] = Dict['authentication_token']
		else:
			Log.Debug('Need to generate a token first from plex.tv')
			userName = Prefs['Plex_User']
			userPwd = Prefs['Plex_Pwd']
			myUrl = 'https://plex.tv/users/sign_in.json'
			# Create the authentication string
			base64string = String.Base64Encode('%s:%s' % (userName, userPwd))
			# Create the header
			MYAUTHHEADER= {}
			MYAUTHHEADER['X-Plex-Product'] = DESCRIPTION
			MYAUTHHEADER['X-Plex-Client-Identifier'] = APPGUID
			MYAUTHHEADER['X-Plex-Version'] = VERSION
			MYAUTHHEADER['Authorization'] = 'Basic ' + base64string
			MYAUTHHEADER['X-Plex-Device-Name'] = NAME
			# Send the request
			try:
				httpResponse = HTTP.Request(myUrl, headers=MYAUTHHEADER, method='POST')
				myToken = JSON.ObjectFromString(httpResponse.content)['user']['authentication_token']
				Log.Debug('Response from plex.tv was : %s' %(httpResponse.headers["status"]))
			except:
				Log.Critical('Exception happend when trying to get a token from plex.tv')
				Log.Critical('Returned answer was %s' %httpResponse.content)
				Log.Critical('Status was: %s' %httpResponse.headers) 			
			Dict['authentication_token'] = myToken
			Dict.Save()
	else:
			Log.Debug('Authentication disabled')
	ValidatePrefs()
	logPrefs()

####################################################################################################
# Main menu
####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
@route(PREFIX + '/MainMenu')
def MainMenu(random=0):
	Log.Debug("**********  Starting MainMenu  **********")
	oc = ObjectContainer()
	try:
		sections = XML.ElementFromURL('http://127.0.0.1:32400/library/sections', headers=MYHEADER).xpath('//Directory')
		for section in sections:
			sectiontype = section.get('type')
			if sectiontype != "photo":
				title = section.get('title')
				key = section.get('key')
				paths = section.xpath('Location/@path')
				Log.Debug("Title of section is %s with a key of %s and a path of : %s" %(title, key, paths))
				oc.add(DirectoryObject(key=Callback(backgroundScan, title=title, sectiontype=sectiontype, key=key, random=time.clock(), paths=',,,'.join(paths)), title='Look in section "' + title + '"', summary='Look for unmatched files in "' + title + '"'))
	except:
		Log.Critical("Exception happened in MainMenu")
		raise
	oc.add(PrefsObject(title='Preferences', thumb=R('icon-prefs.png')))
	Log.Debug("**********  Ending MainMenu  **********")
	return oc



####################################################################################################
# Called by the framework every time a user changes the prefs
####################################################################################################
@route(PREFIX + '/ValidatePrefs')
def ValidatePrefs():
	if Prefs['NukeToken']:
		# My master wants to nuke the local store
		Log.Debug('Removing Token from local storage')
		Dict['authentication_token'] = 'NuKeMe'
		Dict.Save()
	# Lets get the token again, in case credentials are switched, or token is deleted
	global MYHEADER
#	MYHEADER['X-Plex-Token'] = getToken()
	if Prefs['NukeToken']:
		Log.Debug('Resetting flag to nuke token')
		# My master has nuked the local store, so reset the prefs flag
		myHTTPPrefix = 'http://127.0.0.1:32400/:/plugins/com.plexapp.plugins.findUnmatch/prefs/'
		myURL = myHTTPPrefix + 'set?NukeToken=0'
		Log.Debug('Prefs Sending : ' + myURL)
		HTTP.Request(myURL, immediate=True, headers=MYHEADER)
		# Get new token
		getToken()
		
#		MYHEADER['X-Plex-Token'] = getToken()
	# If the old setting from v0.0.1.20 and before that allowed scanning all extensions, then update to the new setting.
	if Prefs['VALID_EXTENSIONS'].lower() == 'all': 
		Log.Debug("VALID_EXTENSIONS=all, setting ALL_EXTENSIONS to True and resetting VALID_EXTENSIONS")
		HTTP.Request('http://127.0.0.1:32400/:/plugins/com.plexapp.plugins.findUnmatch/prefs/set?VALID_EXTENSIONS=', immediate=True, headers=MYHEADER)
		HTTP.Request('http://127.0.0.1:32400/:/plugins/com.plexapp.plugins.findUnmatch/prefs/set?ALL_EXTENSIONS=True', immediate=True, headers=MYHEADER)
	# Do we need to reset the extentions?
	if Prefs['RESET_EXTENTIONS']:
		ResetExtensions()
	


####################################################################################################
# Reset the Media Extentions to the defaults
####################################################################################################
@route(PREFIX + '/ResetExtensions')
def ResetExtensions():
	Log.Debug("Resetting Extensions in Preferences.")
	myHTTPPrefix = 'http://127.0.0.1:32400/:/plugins/com.plexapp.plugins.findUnmatch/prefs/'
	myURL = myHTTPPrefix + 'set?RESET_EXTENTIONS=False&VALID_EXTENSIONS=&IGNORED_FILES=&IGNORED_DIRS=&IGNORED_EXTENSIONS='
	Log.Debug('Prefs Sending : ' + myURL)
	HTTP.Request(myURL, immediate=True, headers=MYHEADER)

####################################################################################################
# Scan Filesystem for a section
####################################################################################################
@route(PREFIX + '/scanFiles')
def scanFiles(title, key, paths):

#def scanFiles(title, key, sectiontype, paths):

	Log.Debug("*******  Starting scanFiles  ***********")
	global bScanStatus
	files = []
	try:
#		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = 'http://127.0.0.1:32400' + key + "/all"
		Log.Debug("Paths to scan: %s" %(paths.split(',,,')))
		for myPath in paths.split(',,,'):
			files.extend(listTree(myPath))
		Log.Debug("********  Files found are the following: ***************")
		Log.Debug(files)
		# Check for no files
		if files == '':
			bScanStatus = 90
			Log.Debug("*******  scanFiles: no files found: files='' ***********")
		elif files == []:
			bScanStatus = 90
			Log.Debug("*******  scanFiles: no files found: files=[] ***********")
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
	# Convert IGNORED_FILES to a list. Replace gets rid of any space after the comma
	ignoredFilesList= Prefs['IGNORED_FILES'].replace(', ',',').split(',')
	# If the directory is in the ignore list don't process it.
	# If top is a drive ex: N:\ os.path.basename() returns an empty string causing a false positive unless we check for an empty string.
	if os.path.basename(os.path.normpath(top)).lower() in Prefs['IGNORED_DIRS'].lower() and os.path.basename(os.path.normpath(top)) != '':
		Log.Debug("Directory is in IGNORED_DIRS: %s" %(top))
		return r
	# Check if top without os.path.basename is in the ignore dirs list.
	elif os.path.normpath(top).lower() in Prefs['IGNORED_DIRS'].lower():
		Log.Debug("Directory is in IGNORED_DIRS: %s" %(top))
		return r
	try:
		if not os.path.exists(top):
			Log.Debug("The file share [%s] is not mounted" %(top))
			return r
		# If enabled, read in .plexignore if it exists
		if Prefs['ENABLE_PLEXIGNORE']:
			if os.path.exists(top + '/.plexignore'):
				Log.Debug("Found .plexignore in: %s" %(top))
				plexignore.append(readPlexignore(top + '/.plexignore'))
			else:
				# If there is no .plexignore then add empty list to plexignore stack
				plexignore.append([])
			# Collapse plexignore into one table with itertools.chain.from_iterable()
			# and remove duplicates with set() and convert back to list with list()
			plexignoreList = list(set(itertools.chain.from_iterable(plexignore)))
#			Log.Debug("plexignoreList is: %s" %(plexignoreList))		
		for f in os.listdir(top):
			pathname = os.path.join(top, f)
			# If the pathname is a dir, scan into it
			if os.path.isdir(pathname):
				r = listTree(pathname, r, plexignore)
				if Prefs['ENABLE_PLEXIGNORE']:
					Log.Debug("plexignoreList is: %s" %(plexignoreList))
			elif os.path.isfile(pathname):
				myext = os.path.splitext(pathname)[1].lower().rstrip("']")
				fname = os.path.split(pathname)[1].lower()
				#################################
				# Look for excluded files
				caught=0
				# Look for filename in IGNORED_FILES. NOTE: Won't catch wildcards, we check wildcards further down.
				if fname in Prefs['IGNORED_FILES'].lower():
					if (display_ignores): Log.Debug("Ignoring %s, it is in the ignored files list." %(pathname))
					continue
				# Look for file extension in IGNORED_EXTENSIONS
				elif (myext in Prefs['IGNORED_EXTENSIONS'].lower()) and myext != '':
					if (display_ignores): Log.Debug("Ignoring %s, it is in the ignored extentions list" %(pathname))
					continue
				# Ignore the file if it's extension is not in VALID_EXTENSIONS and ALL_EXTENSIONS is not set to true.
				elif (myext not in Prefs['VALID_EXTENSIONS'].lower() and not Prefs['ALL_EXTENSIONS']):
					if (display_ignores): Log.Debug("Ignoring %s, it is not in VALID_EXTENSIONS" %(pathname))
					continue
				# Ignore Linux style hidden files.
				elif fnmatch.fnmatch(fname, ".*") and Prefs['IGNORE_HIDDEN']:
					if (display_ignores): Log.Debug("Ignoring hidden file: %s" %(pathname))
					continue
				###############################################
				# Search the ignoredFilesList for a match against the current file.
				# Needed for wildcards. Ugly but it works.
				for ignoredItem in ignoredFilesList:
					if fnmatch.fnmatch(fname, ignoredItem):
						if (display_ignores): Log.Debug("Ignoring %s because it matches %s in the ignored files list" %(pathname, ignoredItem))
						caught=1
						break
				if caught: continue
				###############################################
				# Look to see if the file has a match in plexignoreList
				if Prefs['ENABLE_PLEXIGNORE']:
					for ignore in plexignoreList:
						if fnmatch.fnmatch(pathname, "*" + ignore + "*"):
							if (display_ignores): Log.Debug("Ignoring %s because it matches %s from .plexignore" %(pathname, ignore))
							caught=1
							break
					if caught: continue
				#################################
				bScanStatusCount += 1
				Log.Debug("Found valid file #%s named: %s" %(bScanStatusCount, pathname))
				filename = urllib.unquote(pathname).decode('utf8')
				composed_filename = unicodedata.normalize('NFKC', filename)
				filename = urllib.quote(composed_filename.encode('utf8'))
				r.append(filename)
			else:
				Log.Debug("Warning: %s was not seen as a file or dir." %(pathname))		
		# Remove last item in plexignore, then reset plexignoreList
		if Prefs['ENABLE_PLEXIGNORE']: plexignore.pop(); plexignoreList = list(set(itertools.chain.from_iterable(plexignore)))
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
	global myResults
	global bScanStatusCount
	myResults = []
	Log.Debug("******* Start findUnmatchedFiles ******")
	# Convert IGNORED_FILES to a list. Replace gets rid of any space after the comma
	ignoredFilesList= Prefs['IGNORED_FILES'].replace(', ',',').split(',')
	Log.Debug("*********************** Database paths: *******************************************")
	Log.Debug(myMediaPaths)
	Log.Debug("*********************** FileSystem Paths: *****************************************")
	files = str(files)[2:-2].replace("'", "").split(', ')
	Log.Debug(files)
	for filePath in files:
		# Decode filePath 
		bScanStatusCount += 1
		filePath2 = urllib.unquote(filePath).decode('utf8')
		Log.Debug("Handling file #%s: %s" %(bScanStatusCount, filePath2))
		# If the file is not in the database, figure out what to do.
		if filePath not in myMediaPaths:
			Log.Debug("Missing: %s ???" %(filePath2))
			myext = os.path.splitext(filePath)[1].lower()
			cext = myext.rstrip("']")
			fname = os.path.split(filePath2)[1].lower()
			if (fname in Prefs['IGNORED_FILES'].lower()):
				# Filename is in ignored files, won't catch wildcards
				Log.Debug("File is part of ignored files.")
				continue
			elif (cext in Prefs['IGNORED_EXTENSIONS'].lower()):
				# File extension in in ignored extensions
				Log.Debug("File is part of ignored extentions")
				continue
			elif (cext not in Prefs['VALID_EXTENSIONS'].lower() and Prefs['VALID_EXTENSIONS'].lower() != 'all' and not Prefs['ALL_EXTENSIONS']):
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
# Write the current Prefs to the log file.
####################################################################################################
@route(PREFIX + '/logPrefs')
def logPrefs():
	Log.Debug("*********  Starting to get User Prefs  ***************")
	# If the old setting from v0.0.1.20 and before that allowed scanning all extensions, then update to the new setting.
	if Prefs['VALID_EXTENSIONS'].lower() == 'all': ValidatePrefs()
	Log.Debug("'http://127.0.0.1:32400' is : %s" %('http://127.0.0.1:32400'))
	Log.Debug("ALL_EXTENSIONS is : %s" %(Prefs['ALL_EXTENSIONS']))
	Log.Debug("VALID_EXTENSIONS from prefs are : %s" %(Prefs['VALID_EXTENSIONS']))
	Log.Debug("IGNORED_FILES from prefs are : %s" %(Prefs['IGNORED_FILES']))
	Log.Debug("IGNORED_DIRS from prefs are : %s" %(Prefs['IGNORED_DIRS']))
	Log.Debug("IGNORED_EXTENSIONS from prefs are : %s" %(Prefs['IGNORED_EXTENSIONS']))
	Log.Debug("IGNORE_HIDDEN is : %s" %(Prefs['IGNORE_HIDDEN']))
	Log.Debug("ENABLE_PLEXIGNORE is : %s" %(Prefs['ENABLE_PLEXIGNORE']))
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
		myMedias = XML.ElementFromURL(myMediaURL, headers=MYHEADER).xpath('//Video')
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
				Log.Debug("Media #%s from database: '%s' with a path of : %s" %(bScanStatusCount, title, composed_filename))
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
		myMedias = XML.ElementFromURL(myMediaURL, headers=MYHEADER).xpath('//Directory')
		bScanStatusCountOf = len(myMedias)
		for myMedia in myMedias:
			bScanStatusCount += 1
			ratingKey = myMedia.get("ratingKey")
			myURL = "http://127.0.0.1:32400/library/metadata/" + ratingKey + "/allLeaves"
			Log.Debug("Show %s of %s with a RatingKey of %s at myURL: %s" %(bScanStatusCount, bScanStatusCountOf, ratingKey, myURL))
			myMedias2 = XML.ElementFromURL(myURL, headers=MYHEADER).xpath('//Video')
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
					Log.Debug("Media from database: '%s' with a path of : %s" %(title, composed_filename))
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
		myMedias = XML.ElementFromURL(myMediaURL, headers=MYHEADER).xpath('//Directory')
		bScanStatusCountOf = len(myMedias)
		for myMedia in myMedias:
			bScanStatusCount += 1
			ratingKey = myMedia.get("ratingKey")
			myURL = "http://127.0.0.1:32400/library/metadata/" + ratingKey + "/allLeaves"
			Log.Debug("%s of %s with a RatingKey of %s at myURL: %s" %(bScanStatusCount, bScanStatusCountOf, ratingKey, myURL))
			myMedias2 = XML.ElementFromURL(myURL, headers=MYHEADER).xpath('//Track')
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
				Log.Debug("Media from database: '%s' with a path of : %s" %(title, composed_filename))
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
def backgroundScan(title='', key='', sectiontype='', random=0, paths=[], statusCheck=0):
#def backgroundScan(title, key, sectiontype, random=0, paths=[]):
	Log.Debug("******* Starting backgroundScan *********")
	# Current status of the Background Scanner:
	# 0=not running, 1=db, 2=filesystem, 3=compare, 4=complete
	# Errors: 90=filesystem empty, 91=unknown section type, 99=Other Error
	global bScanStatus
	# Current status count (ex. "Show 2 of 31")
	global bScanStatusCount
	global bScanStatusCountOf
	try:
		if bScanStatus == 0 and not statusCheck:
			bScanStatusCount = 0
			bScanStatusCountOf = 0
			# Start scanner
			Thread.Create(backgroundScanThread, globalize=True, title=title, key=key, sectiontype=sectiontype, paths=paths)
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
		# Sometimes a scanStatus check will happen when a scan is running. Usually from something weird in the web client. This prevents the scan from restarting
		elif bScanStatus == 0 and statusCheck:
			Log.Debug("backgroundScan statusCheck is set and no scan is running")
			oc2 = ObjectContainer(title1="Scan is not running.", no_history=True)
			oc2.add(DirectoryObject(key=Callback(results, title=title), title="Get the last results."))
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="Go to the Main Menu"))
			return oc2
			# Summary to add to the status
		summary = "The Plex client will only wait a few seconds for us to work, so we run it in the background. This requires you to keep checking on the status until it is complete. \n\n"
		if bScanStatus == 1:
			# Scanning Database
			summary = summary + "The Database is being scanned. \nScanning " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf) + ". \nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Scanning Database " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf) + ".", no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), statusCheck=1), title="Scanning the database. Check Status.", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), statusCheck=1), title="Scanning " + str(bScanStatusCount) + " of " + str(bScanStatusCountOf), summary=summary))
		elif bScanStatus == 2:
			# Scanning Filesystem
			summary = summary + "The filesystem is being scanned. \n Scanning file #" + str(bScanStatusCount) + " of about " + str(bScanStatusCountOf) + ".\nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Scanning Filesystem #" + str(bScanStatusCount) + " of about " + str(bScanStatusCountOf) + ".", no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), statusCheck=1), title="Scanning filesystem. Check Status", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), statusCheck=1), title="Scanning file #" + str(bScanStatusCount), summary=summary))
		elif bScanStatus == 3:
			# Comparing results
			summary = summary + "Comparing the results. \n Scanning #" + str(bScanStatusCount) + ".\nPlease wait a few seconds and check the status again."
			oc2 = ObjectContainer(title1="Comparing #" + str(bScanStatusCount), no_history=True)
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), statusCheck=1), title="Comparing the results. Check Status", summary=summary))
			oc2.add(DirectoryObject(key=Callback(backgroundScan, random=time.clock(), statusCheck=1), title="File #" + str(bScanStatusCount), summary=summary))
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
		elif bScanStatus == 91:
			# scanFiles returned no files
			summary = "Unknown section type returned."
			oc2 = ObjectContainer(title1="Results", no_history=True)
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="*** Unknown section type. ***", summary=summary))
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="*** Please submit logs. ***", summary=summary))
			bScanStatus = 0
		elif bScanStatus == 99:
			# Error condition set by scanner
			summary = "An internal error has occurred. Please check the logs"
			oc2 = ObjectContainer(title1="Internal Error Detected. Please check the logs",no_history=True)
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="An internal error has occurred.", summary=summary))
			oc2.add(DirectoryObject(key=Callback(MainMenu, random=time.clock()), title="*** Please submit logs. ***", summary=summary))
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
def backgroundScanThread(title, key, sectiontype, paths):
	Log.Debug("*******  Starting backgroundScanThread  ***********")
	global bScanStatus
	global bScanStatusCount
	global bScanStatusCountOf	
	try:
		bScanStatus = 1
		# Print the latest Prefs to the log file.
		logPrefs()
		Log.Debug("Section type is %s" %(sectiontype))
		myMediaURL = 'http://127.0.0.1:32400/library/sections/' + key + "/all"
		Log.Debug("Path to medias in section is %s" %(myMediaURL))
		# Scan the database based on the type of section
		if sectiontype == "movie":
			myMediaPaths = scanMovieDB(myMediaURL)
			filecount = bScanStatusCount
		elif sectiontype == "artist":
			myMediaPaths, filecount = scanArtistDB(myMediaURL)
		elif sectiontype == "show":
			myMediaPaths, filecount = scanShowDB(myMediaURL)
		else:
			Log.Debug("Error: unknown section type: %s" %(sectiontype))
			bScanStatus = 91
		Log.Debug("**********  Section filepath as stored in the database are: %s  *************" %(myMediaPaths))
		# Stop scanner on error
		if bScanStatus >= 90: return
		# Scan the filesystem
		bScanStatus = 2
		bScanStatusCount = 0
		bScanStatusCountOf = filecount
		files = scanFiles(title, key, paths)
# GED		files = scanFiles(title, key, sectiontype, paths)
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
		Log.Debug("*******  Ending backgroundScanThread  ***********")
		return
	except:
		Log.Critical("Exception happened in backgroundScanThread")
		bScanStatus = 99
		raise
	Log.Debug("*******  Ending backgroundScanThread  ***********")
