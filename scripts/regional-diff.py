#!/usr/bin/python

from __future__ import print_function
import argparse, urllib, urllib2, re, gzip, subprocess, os, sys, shlex
from lxml import etree

osmosis_bin = "/usr/bin/osmosis"
parser = argparse.ArgumentParser(\
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description='Print all way ids of the latest \
minutely replication diff file from planet.openstreetmap.org ',
                epilog='''
''')

parser.add_argument("-v", "--verbose", action="store_true", help="increase verbosity")
parser.add_argument("-f", "--file", action="store", help="use local osc.gz file \
(instead of downloading the latest file")
args = parser.parse_args()

# Verbose print function taken from: http://stackoverflow.com/a/5980173
if args.verbose:
    def verboseprint(*args):
        # Print each argument separately so caller doesn't need to
        # stuff everything to be printed into a single string
        print ("VERBOSE:", *args, file=sys.stderr)
else:   
    verboseprint = lambda *a: None      # do-nothing function

class PlanetOsm:
    # TODO: figure out what happens when 000 changes. Currently (2014-06-09)
    # state.txt does not show 000 in it.
    __replication_url = 'http://planet.openstreetmap.org/replication/'
    __minutely_base_url = __replication_url + "minute/"
    __minutely_url = __minutely_base_url + "000/"
    __minutelyDiffFilename = ""
    __state_url = __minutely_base_url + "state.txt"
    __content_state = ""
    __content_diff = ""

    __ways = []
    sequenceNumber = ""

    def __init__(self):
        self.update()

    def __downloadStateFile(self):
        verboseprint("Downloading state.txt...")
        response = urllib2.urlopen(self.__state_url)
        self.__content_state = response.read()
        # verboseprint("Content of state.txt:\n", self.__content_state)
        self.sequenceNumber = self.__getCurrentSequenceNumber()

    def __getCurrentSequenceNumber(self):
        sequenceNumberLine = re.findall('.*sequenceNumber=\d*', self.__content_state)[0]
        return re.split('=', sequenceNumberLine)[1]

    def __downloadDiffFile(self):
        self.__minutelyDiffFilename = self.__splitSequenceNumber(2) + ".osc.gz"
        minutelyDiffUrl = self.__minutely_url + self.__splitSequenceNumber(1) + "/" + self.__minutelyDiffFilename

        verboseprint("URL of latest minutely diff:", minutelyDiffUrl)
        verboseprint("Downloading " + self.__minutelyDiffFilename + "...")

        urllib.urlretrieve(minutelyDiffUrl, self.__minutelyDiffFilename)

    def __loadDiffFile(self):
        f = gzip.open(self.__minutelyDiffFilename, 'rb')
        self.__content_diff = f.read()
        f.close()
        # verboseprint("Content of " + self.__minutelyDiffFilename + ":")
        # verboseprint(self.__content_diff)

    def __osmosis(self):
        if not os.path.isfile(osmosis_bin):
            return

        devnull = open('/dev/null', 'w')
        args = shlex.split(osmosis_bin + ' --read-xml-change - outPipe.0="change" \
--simplify-change inPipe.0="change" outPipe.0="cleaned" \
--read-empty outPipe.0="empty" --apply-change inPipe.0="empty" \
inPipe.1="cleaned" outPipe.0="osm" --bounding-polygon \
inPipe.0="osm" file="vorarlberg.poly" --write-xml -')

        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=devnull)
        devnull.close()
        cropped_diff = p.communicate(self.__content_diff)
        p.stdin.close()
        self.__content_diff = cropped_diff[0]

    def __readWayNodes(self):
        verboseprint("parsing XML...")
        root = etree.fromstring(self.__content_diff)
        if root.tag == "osmChange":
            verboseprint("Detected osmChange file")
            verboseprint("modified way ids...")
            # iterate through all changesets (which should be "modify", "delete" or "create")
            for changeset in root:
                if changeset.tag == "modify" or changeset.tag == "delete" or changeset.tag == "create":
                    # we are only interested in ways
                    for item in changeset:
                        if item.tag == "way":
                            self.__ways.append("way" + item.attrib["id"])
                        elif item.tag == "relation":
                            self.__ways.append("relation" + item.attrib["id"])
                else:
                    print ("WARNING: found new change type: " + changeset.tag)
        elif root.tag == "osm":
            verboseprint("Detected osm file")
            verboseprint("way ids...")
            for item in root:
                if item.tag == "way":
                    self.__ways.append("way" + item.attrib["id"])
                elif item.tag == "relation":
                    self.__ways.append("relation" + item.attrib["id"])

        else:
            print ("ERROR: not an osm oder osm-change file")
            os.system(2)

    def __splitSequenceNumber(self, x):
        m = re.search('(...)(...)', self.sequenceNumber)
        if not m:
            raise Exception("Current Sequence Number can not be extracted! Please check state.txt file manually.")
        return m.group(x)

    # download state.txt and diff file and update all variables
    def update(self):
        if args.file:
            verboseprint("skipping download. Using localfile: " + args.file)
            self.__minutelyDiffFilename = args.file
        else:
            self.__downloadStateFile()
            self.__downloadDiffFile()

        self.__loadDiffFile()
        self.__osmosis()
        self.__readWayNodes()

    def printWayIds(self):
        for way in self.__ways:
            print (way)

if __name__ == '__main__':
    posm = PlanetOsm()
    posm.printWayIds()

