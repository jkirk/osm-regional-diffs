#!/usr/bin/python
#
# download stats.txt and output current sequence number

import urllib2
response = urllib2.urlopen('http://planet.openstreetmap.org/replication/minute/state.txt')
html = response.read()
print html
