The Plex-FindUnmatched is a plugin for Plex Media Server, that will scan sections in the PMS database, and compare the medias found in there with the filesystem, listing medias that Plex are missing.


Work To Do:

https://github.com/ukdtom/PLex-FindUnmatched/issues

Installation:

Download this either by forking it, or simply pressing the "Download zip" button to the right.

Then create a directory named <PMS Root Dir>/Library/Plex Media Server/Plug-ins/FindUnmatched.bundle
Put contents dir from zip in this directory, and restart PMS

Currently, output from this plugin is sadly only reported in the logfile, named <PMS Root Dir>/Library/Plex Media Server/Logs/PMS Plugin Logs/com.plexapp.plugins.findUnmatch.log, where you should look for a line containing the following:

"The END RESULT" without the quotes

Use @ One risk

Best Regards

dane22

