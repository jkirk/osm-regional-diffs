#!/usr/bin/python
#
# download stats.txt and output current sequence number

import urllib2, re

base_minurl = 'http://planet.openstreetmap.org/replication/minute/000/'

response = urllib2.urlopen('http://planet.openstreetmap.org/replication/minute/state.txt')
html = response.read()
sequenceNumber = re.findall('.*sequenceNumber=\d*', html)[0]
currentSequnceNumber = re.split('=', sequenceNumber)[1]
m = re.search('(...)(...)', currentSequnceNumber)

if m:
    print base_minurl + m.group(1) + "/" + m.group(2) + ".osc.gz"
