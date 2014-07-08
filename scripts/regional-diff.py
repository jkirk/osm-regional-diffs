#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import argparse, urllib, urllib2, re, gzip, subprocess, os, sys, shlex
import datetime
import PyRSS2Gen
from lxml import etree

osmosis_bin = "/usr/bin/osmosis"
parser = argparse.ArgumentParser(\
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description='Print report of all modified ways and relations \
from Vorarlberg of the latest minutely or hourly replication diff file \
from planet.openstreetmap.org (or by a given diff file)',
                epilog='''
''')

parser.add_argument("-v", "--verbose", action="store_true", help="increase verbosity")
filegroup = parser.add_mutually_exclusive_group()
filegroup.add_argument("-M", "--minutely", action="store_true", default=True,
help="use minutely diff file from planet.openstreetmap.org (default)")
filegroup.add_argument("-H", "--hourly", action="store_true",
help="use hourly diff file from planet.openstreetmap.org")
filegroup.add_argument("-f", "--file", action="store", help="use local osc.gz diff file \
(instead of downloading the latest diff file from planet.openstreetmap.org)")
filegroup.add_argument("--osmfile", action="store", help="use local osm file \
(from osmosis or overpass API)")
output = parser.add_mutually_exclusive_group()
output.add_argument("--report", action="store_true", default=True, help="output \
report to stdout (default)")
output.add_argument("--ids-only", action="store_true", help="output all way and \
relation IDs from given diff")
output.add_argument("--ql-only", action="store_true", help="output Overpass QL")
output.add_argument("--rss-file", action="store", help="output report as rss file")
args = parser.parse_args()

# Verbose print function taken from: http://stackoverflow.com/a/5980173
if args.verbose:
    def verboseprint(*args):
        # Print each argument separately so caller doesn't need to
        # stuff everything to be printed into a single string
        print ("VERBOSE:", *args, file=sys.stderr)
else:   
    verboseprint = lambda *a: None      # do-nothing function

class OverpassQL:
    __ways = []
    __relations = []

    def __init__(self, ways, relations):
        self.__ways = ways;
        self.__relations = relations

    def getBikerouteways(self):
        ql_bikerouteways = '(\n'
        for way in self.__ways:
            ql_bikerouteways += '  way(' + way + ');\n'
        ql_bikerouteways += ');\n'
        ql_bikerouteways += 'rel(bw)[route="bicycle"]->.cycleroutes;\n'
        ql_bikerouteways += 'way(r.cycleroutes)->.cycleways;\n'
        ql_bikerouteways += '(\n'
        for way in self.__ways:
            ql_bikerouteways += '  way.cycleways(' + way + ');\n'
        ql_bikerouteways += ')->.bikerouteways;\n'
        return ql_bikerouteways

    def getCycleways(self):
        ql_cycleways = '(\n'
        for way in self.__ways:
            ql_cycleways += '  way(' + way + ')[highway="cycleway"];\n'
        ql_cycleways += ')->.cycleways;\n'
        return ql_cycleways

    def getBikeroutes(self):
        ql_bikeroutes = '(\n'
        for relation in self.__relations:
            ql_bikeroutes += '  relation(' + relation + ')[route="bicycle"];\n'
        ql_bikeroutes+= ')->.bikeroutes;\n'
        return ql_bikeroutes

    def getBicycleallowed(self):
        ql_bicycleallowed = '(\n'
        for way in self.__ways:
            ql_bicycleallowed += '  way(' + way + ')[highway~"footway|track|service|path"][bicycle!="private"][bicycle!="no"][bicycle];\n'
        ql_bicycleallowed += ')->.bicycleallowed;\n'
        return ql_bicycleallowed

    def QL(self):
        overpass = self.getBikerouteways()
        overpass += self.getCycleways()
        overpass += self.getBikeroutes()
        overpass += self.getBicycleallowed()
        overpass += '(\n'
        overpass += ' .bikerouteways;\n'
        overpass += ' .cycleways;\n'
        overpass += ' .bikeroutes;\n'
        overpass += ' .bicycleallowed;\n'
        overpass += ');\n'
        overpass += 'out meta;\n'
        return overpass

    def compactQL(self):
        return re.sub(r'(;|\() *', r'\1', self.QL().replace('\n', ''))

    def Url(self):
        return "http://overpass-api.de/api/interpreter?data=" + self.compactQL()

    def EncodedUrl(self):
        return "http://overpass-api.de/api/interpreter?data=" + urllib.quote_plus(self.compactQL())

class PlanetOsm:
    __replication_url = 'http://planet.openstreetmap.org/replication/'
    if args.hourly:
        __diff_base_url = __replication_url + "hour/"
    else:
        __diff_base_url = __replication_url + "minute/"
    # TODO: minutelyDiffFile should be deleted after download
    __diffFilename = ""
    __state_url = __diff_base_url + "state.txt"
    __content_state = ""
    __content_diff = ""

    __ways = []
    __relations = []
    sequenceNumber = ""

    def __init__(self):
        self.update()

    def __downloadStateFile(self):
        verboseprint("Downloading state.txt...")
        verboseprint("URL: " + self.__state_url)
        response = urllib2.urlopen(self.__state_url)
        self.__content_state = response.read()
        verboseprint("Timestamp of state.txt:", self.__content_state.splitlines()[0])
        verboseprint("Sequencenumber of state.txt:", self.__content_state.splitlines()[1])
        self.sequenceNumber = self.__getCurrentSequenceNumber()

    def __getCurrentSequenceNumber(self):
        sequenceNumberLine = re.findall('.*sequenceNumber=\d*', self.__content_state)[0]
        return re.split('=', sequenceNumberLine)[1]

    def __downloadDiffFile(self):
        self.__diffFilename = self.__splitSequenceNumber(3) + ".osc.gz"
        diffUrl = self.__diff_base_url + self.__splitSequenceNumber(1) + "/" + self.__splitSequenceNumber(2) + "/" + self.__diffFilename

        verboseprint("URL of latest minutely diff:", diffUrl)
        verboseprint("Downloading " + self.__diffFilename + "...")

        urllib.urlretrieve(diffUrl, self.__diffFilename)

    def __downloadOverpass(self, ql):
        verboseprint("Overpass-URL: " + ql.Url())
        verboseprint("Overpass-Encoded-URL: " + ql.Url())
        request = urllib2.Request(ql.Url().split('?')[0], ql.Url().split('?')[1])
        response = urllib2.urlopen(request)
        self.__content_diff = response.read()

    def __loadDiffFile(self):
        f = gzip.open(self.__diffFilename, 'rb')
        self.__content_diff = f.read()
        f.close()
        # verboseprint("Content of " + self.__diffFilename + ":")
        # verboseprint(self.__content_diff)

    def __loadOsmFile(self):
        f = open(self.__minutelyOsmFilename, 'rb')
        self.__content_diff = f.read()
        f.close()

    def __osmosis(self):
        if not os.path.isfile(osmosis_bin):
            return

        devnull = open('/dev/null', 'w')

        args_simplify = shlex.split(osmosis_bin + ' --read-xml-change - outPipe.0="change" \
--simplify-change inPipe.0="change"  \
--write-xml-change -')

        ps = subprocess.Popen(args_simplify, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=devnull)
        simplified_diff = ps.communicate(self.__content_diff)
        ps.stdin.close()

        # change osm-item status from deleted to modified, because osmosis ignores deleted nodes when creating osm-file
        changed_stream = re.sub('delete>','modify>',simplified_diff[0])
        #changed_stream = simplified_diff[0]


        args_convert2osm = shlex.split(osmosis_bin + ' --read-xml-change - outPipe.0="change" \
--read-empty outPipe.0="empty" \
--apply-change inPipe.0="empty" inPipe.1="change" \
--write-xml -')

        pc = subprocess.Popen(args_convert2osm, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=devnull)
        converted_diff = pc.communicate(changed_stream)
        pc.stdin.close()

        args_filter = shlex.split(osmosis_bin + ' --read-xml - \
--tag-filter accept-ways highway=* \
--tag-filter reject-ways highway=motorway,motorway_link,trunk,trunk_link,bus_guideway,raceway \
--tag-filter accept-relations route=bicycle \
--write-xml -')
        
        pf = subprocess.Popen(args_filter, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=devnull)
        filtered_diff = pf.communicate(converted_diff[0])
        pf.stdin.close()

        #todo: 
        # • simplify-change -OK
        # • per regex <deleted> → <modified> im osc -OK
        # • convert2xml -OK
        # • filter tags
        # • add missing nodes via overpass
        # • cut -OK

# original query
#        args = shlex.split(osmosis_bin + ' --read-xml-change - outPipe.0="change" \
    #--simplify-change inPipe.0="change" outPipe.0="cleaned" \
    #--read-empty outPipe.0="empty" \
    #--apply-change inPipe.0="empty" inPipe.1="cleaned" outPipe.0="osm" \
    #--bounding-polygon inPipe.0="osm" file="vorarlberg.poly" \
    #--write-xml -')

# query to read in changed_stream
        args = shlex.split(osmosis_bin + ' --read-xml - outPipe.0="osm" \
--bounding-polygon inPipe.0="osm" file="vorarlberg.poly" \
--write-xml -')

        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=devnull)
        cropped_diff = p.communicate(filtered_diff[0])
        p.stdin.close()
        devnull.close()
        self.__content_diff = cropped_diff[0]

    # TODO: change to __readModifiedWaysAndRelations
    # TODO: __content_diff should be __content
    def __readWayNodes(self):
        self.__ways = []
        self.__relations = []
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
                            self.__ways.append(item.attrib["id"])
                        elif item.tag == "relation":
                            self.__relations.append(item.attrib["id"])
                else:
                    print ("WARNING: found new change type: " + changeset.tag)
        elif root.tag == "osm":
            verboseprint("Detected osm file")
            verboseprint("way ids...")
            for item in root:
                if item.tag == "way":
                    self.__ways.append(item.attrib["id"])
                elif item.tag == "relation":
                    self.__relations.append(item.attrib["id"])

        else:
            print ("ERROR: not an osm oder osm-change file")
            os.system(2)

    def printChangeFeed(self):
        if args.file:
            print ('The following ways and relations (in Vorarlberg) have been modified in ' + args.file)
        else:
            print ('The following ways and relations (in Vorarlberg) have been modified since ' + self.__content_state.splitlines()[0] + ':')
        verboseprint("parsing XML...")
        root = etree.fromstring(self.__content_diff)
        if root.tag == "osm":
            verboseprint("Detected osm file")
            verboseprint("way and relation ids...")
            for item in root:
                if item.tag == "way":
                    print ('WAY: ' +  item.attrib["id"])
                    print ('  http://www.openstreetmap.org/way/' + item.attrib["id"] + '/history')
                    print ('  http://www.openstreetmap.org/changeset/' + item.attrib["changeset"])
                elif item.tag == "relation":
                    print ('RELATION: ' +  item.attrib["id"])
                    print ('  http://www.openstreetmap.org/relation/' + item.attrib["id"] + '/history')
                    print ('  http://www.openstreetmap.org/changeset/' + item.attrib["changeset"])
        else:
            print ("ERROR: not an osm file")

    def generateRssFeed(self):
        rssitems = []
        verboseprint("parsing XML...")
        root = etree.fromstring(self.__content_diff)
        if root.tag == "osm":
            verboseprint("Detected osm file")
            verboseprint("way and relation ids...")
            for item in root:
                if item.tag == "way":
                    title = "Modified way: " + item.attrib["id"]
                    link = 'http://www.openstreetmap.org/way/' + item.attrib["id"] + '/history'
                    rssitems.append(PyRSS2Gen.RSSItem(title = title, link = link))
                elif item.tag == "relation":
                    title = "Modified relation: " + item.attrib["id"]
                    link = 'http://www.openstreetmap.org/relation/' + item.attrib["id"] + '/history'
                    rssitems.append(PyRSS2Gen.RSSItem(title = title, link = link))
        else:
            print ("ERROR: not an osm file")

        rss = PyRSS2Gen.RSS2(
        title = "Regional Diff feed",
        link = "https://github.com/jkirk/osm-regional-diffs",
        description='All modified ways and relations \
from Vorarlberg of the latest minutely replication diff file \
from planet.openstreetmap.org (or by a given diff file)',
        lastBuildDate = datetime.datetime.utcnow(),
        items = rssitems
        )

        rss.write_xml(open(args.rss_file, "w"))

    def __splitSequenceNumber(self, x):
        m = re.search('(...)(...)(...)', self.sequenceNumber.zfill(9))
        if not m:
            raise Exception("Current Sequence Number could not be extracted! Please check state.txt file manually.")
        return m.group(x)

    # download state.txt and diff file and update all variables
    def update(self):
        if args.file:
            verboseprint("skipping download. Using local diff file (.osc.gz): " + args.file)
            self.__diffFilename = args.file
        elif args.osmfile:
            verboseprint("skipping download. Using local osm file (.osm): " + args.osmfile)
            self.__minutelyOsmFilename = args.osmfile
        else:
            self.__downloadStateFile()
            self.__downloadDiffFile()

        if args.osmfile:
            self.__loadOsmFile()
        else:
            self.__loadDiffFile()
            self.__osmosis()

        self.__readWayNodes()

    def printWayIds(self):
        for way in self.__ways:
            print ("way" + way)

    def printRelationIds(self):
        for relation in self.__relations:
            print ("relation" + relation)

    def printIds(self):
        self.printWayIds()
        self.printRelationIds()

    def printOverpassQL(self):
        ql = OverpassQL(self.__ways, self.__relations)
        print (ql.QL())

    def printCompactOverpassQL(self):
        ql = OverpassQL(self.__ways, self.__relations)
        print (ql.compactQL())

    def printOverpassQLUrl(self):
        ql = OverpassQL(self.__ways, self.__relations)
        print (ql.Url())

    def downloadOverpass(self):
        ql = OverpassQL(self.__ways, self.__relations)
        self.__downloadOverpass(ql)
        # self.__readWayNodes()

if __name__ == '__main__':
    posm = PlanetOsm()
    if args.ids_only:
        posm.printIds()
    elif args.ql_only:
        posm.printOverpassQL()
    else:
        # posm.printCompactOverpassQL()
        # posm.printOverpassQLUrl()
        posm.downloadOverpass()
        if args.rss_file:
            posm.generateRssFeed()
        else:
            posm.printChangeFeed()

