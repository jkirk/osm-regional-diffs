#!/usr/bin/python
#
# download stats.txt and output current sequence number

import urllib2, re
response = urllib2.urlopen('http://planet.openstreetmap.org/replication/minute/state.txt')
html = response.read()
sequenceNumber = re.findall('.*sequenceNumber=\d*', html)[0]
currentSequnceNumber = re.split('=', sequenceNumber)[1]
print currentSequnceNumber
