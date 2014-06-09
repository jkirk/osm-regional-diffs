#!/usr/bin/python
#

import urllib, urllib2, re, sys

# download stats.txt and extract current sequence number
base_minurl = 'http://planet.openstreetmap.org/replication/minute/000/'
response = urllib2.urlopen('http://planet.openstreetmap.org/replication/minute/state.txt')
html = response.read()
print "VERBOSE: Content of state.txt:"
print html
sequenceNumber = re.findall('.*sequenceNumber=\d*', html)[0]
currentSequnceNumber = re.split('=', sequenceNumber)[1]
m = re.search('(...)(...)', currentSequnceNumber)

if not m:
    print "Could not find pattern in sequence number: " + currentSequnceNumber
    sys.exit(1)

minutelyDiffFilename = m.group(2) + ".osc.gz"
minutelyDiffUrl = base_minurl + m.group(1) + "/" + minutelyDiffFilename
print "VERBOSE: URL of latest minutely diff:"
print minutelyDiffUrl

print "VERBOSE: Downloading " + minutelyDiffFilename + "..."
urllib.urlretrieve(minutelyDiffUrl, minutelyDiffFilename)

