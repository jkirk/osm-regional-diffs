#!/usr/bin/python

import argparse, urllib, urllib2, re, gzip
from lxml import etree

parser = argparse.ArgumentParser(\
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description='Print all way ids of latest \
planet.openstreetmap.org - replication diff file',
                epilog='''
''')

parser.add_argument("--verbose", action="store_true", help="increase verbosity")
args = parser.parse_args()

# Verbose print function taken from: http://stackoverflow.com/a/5980173
if args.verbose:
    def verboseprint(*args):
            # Print each argument separately so caller doesn't need to
            # stuff everything to be printed into a single string
            for arg in args:
               print arg,
            print
else:   
    verboseprint = lambda *a: None      # do-nothing function

class PlanetOsm:
    # TODO: figure out what happens when 000 changes. Currently (2014-06-09)
    # state.txt does not show 000 in it.
    __replication_url = 'http://planet.openstreetmap.org/replication/'
    __minutely_base_url = __replication_url + "minute/"
    __minutely_url = __minutely_base_url + "000/"
    __state_url = __minutely_base_url + "state.txt"
    __content_state = ""
    __content_diff = ""

    __ways = []
    sequenceNumber = ""

    def __init__(self):
        self.update()

    def __downloadStateFile(self):
        response = urllib2.urlopen(self.__state_url)
        self.__content_state = response.read()
        verboseprint("VERBOSE: Content of state.txt:\n", self.__content_state)
        self.sequenceNumber = self.__getCurrentSequenceNumber()

    def __getCurrentSequenceNumber(self):
        sequenceNumberLine = re.findall('.*sequenceNumber=\d*', self.__content_state)[0]
        return re.split('=', sequenceNumberLine)[1]

    def __downloadDiffFile(self):
        minutelyDiffFilename = self.__splitSequenceNumber(2) + ".osc.gz"
        minutelyDiffUrl = self.__minutely_url + self.__splitSequenceNumber(1) + "/" + minutelyDiffFilename

        verboseprint("VERBOSE: URL of latest minutely diff:", minutelyDiffUrl)
        verboseprint("VERBOSE: Downloading " + minutelyDiffFilename + "...")

        urllib.urlretrieve(minutelyDiffUrl, minutelyDiffFilename)

        f = gzip.open(minutelyDiffFilename, 'rb')
        self.__content_diff = f.read()
        f.close()
        verboseprint("VERBOSE: Content of " + minutelyDiffFilename + ":")
        verboseprint(self.__content_diff)

    def __readWayNodes(self):
        verboseprint("VERBOSE: parsing XML...")
        root = etree.fromstring(self.__content_diff)

        verboseprint("VERBOSE: modified way ids...")
        # iterate through all changesets (which should be "modify", "delete" or "create")
        for changeset in root:
            if changeset.tag == "modify" or changeset.tag == "delete" or changeset.tag == "create":
                # we are only interested in ways
                for item in changeset:
                    if item.tag == "way":
                        verboseprint(item.attrib["id"])
                        self.__ways.append(item.attrib["id"])
            else:
                print "WARNING: found new change type: " + changeset.tag

    def __splitSequenceNumber(self, x):
        m = re.search('(...)(...)', self.sequenceNumber)
        if not m:
            raise Exception("Current Sequence Number can not be extracted! Please check state.txt file manually.")
        return m.group(x)

    # download state.txt and diff file and update all variables
    def update(self):
        self.__downloadStateFile()
        self.__downloadDiffFile()
        self.__readWayNodes()

    def printWayIds(self):
        for way in self.__ways:
            print way

if __name__ == '__main__':
    posm = PlanetOsm()
    posm.printWayIds()

