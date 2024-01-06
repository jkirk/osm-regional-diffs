#!/usr/bin/env python3
# -*- coding: utf-8 -*-`

import argparse, urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, re, gzip, subprocess, os, sys, shlex
import datetime
import PyRSS2Gen
import tempfile
from lxml import etree

osmosis_bin = "/usr/bin/osmosis"
overpass_server_url = "http://overpass-api.de/api/interpreter?data="
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
output.add_argument("--rss-file", action="store", help="output / append report as rss file")
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
        return overpass_server_url + self.compactQL()

    def EncodedUrl(self):
        return overpass_server_url + urllib.parse.quote_plus(self.compactQL())

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
        response = urllib.request.urlopen(self.__state_url)
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

        urllib.request.urlretrieve(diffUrl, self.__diffFilename)

    def __downloadOverpass(self, ql):
        self.__content_diff = self.__downloadOverpassRetVal(ql.Url())

    def __downloadOverpassRetVal(self, url):
        verboseprint("Overpass-URL: " + url)

        overpass_output = "Error"
        try:
            request = urllib.request.Request(url.split('?')[0], url.split('?')[1])
            response = urllib.request.urlopen(request)
            overpass_output = response.read()
        except:
            e = sys.exc_info()[0]
            print ( "Error in calling overpass server: %s" % e )
            print ( "statement was: " + url )

        return overpass_output

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

    def __osmosisCall(self,args, input_data):
        devnull = open('/dev/null', 'w')
        verboseprint("osmosis call „" + args + "“ started, TIME: " + str(datetime.datetime.now()))
        exe_and_args = shlex.split(osmosis_bin + args)
        p = subprocess.Popen(exe_and_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=devnull)
        output_data = p.communicate(input_data)
        p.stdin.close()
        verboseprint("osmosis pipe end   TIME: " + str(datetime.datetime.now()))
        devnull.close()
        return output_data[0]

    def __osmosis(self):
        if not os.path.isfile(osmosis_bin):
            print ("WARNING: " + osmosis_bin + " not found!")
            return

        args_simplify = ' --read-xml-change - outPipe.0="change" \
--simplify-change inPipe.0="change"  \
--write-xml-change -'
        simplified_diff = self.__osmosisCall(args_simplify, self.__content_diff)

        # change osm-item status from deleted to modified, because osmosis ignores deleted items when creating osm-file
        changed_stream = re.sub('delete>','modify>',simplified_diff)

        args_convert2osm = ' --read-xml-change - outPipe.0="change" \
--read-empty outPipe.0="empty" \
--apply-change inPipe.0="empty" inPipe.1="change" \
--tag-filter accept-ways highway=* \
--tag-filter reject-ways highway=motorway,motorway_link,trunk,trunk_link,bus_guideway,raceway \
--tag-filter accept-relations route=bicycle \
--write-xml -'
        filtered_diff = self.__osmosisCall(args_convert2osm, changed_stream)

        verboseprint("add missing nodes to ways without spatial information: parsing XML...")
        root = etree.fromstring(filtered_diff)
        node_table = {} # python dictionary = hash table for speed. key: node-id; values: 'existing'→1,'to download'→2
        nodes_to_download = [] # extra list for performance reasons

        if root.tag == "osm":
            verboseprint("Detected osm file")
            verboseprint("scanning for existing nodes…")

            # filling hash table of nodes with existing ones
            for item in root:
                if item.tag == "node":
                    node_id = item.attrib["id"]
                    node_table[node_id] = 1
            verboseprint("existing nodes found:" + str(len(node_table)))

            # loop over ways
            for item in root:
                if item.tag != "way":
                    continue

                way_id = item.attrib["id"]
                verboseprint("checking way-id „" + way_id + "“")

                # loop over way members (nodes)
                way_has_spatial_information = 0
                for member in item:
                    if member.tag != "nd":
                        continue

                    node_id = member.attrib["ref"]
                    if node_id in node_table:
                        status = node_table[node_id]
                        way_has_spatial_information = 1
                        verboseprint("node (" + node_id + ") found, status: " + str(status))
                        break

                if way_has_spatial_information: # lack of "continue 2"
                  continue
                # node_id is set on last node of way, add it to download list
                node_table[node_id] = 2
                nodes_to_download.append(node_id)
                verboseprint("no spatial information found, adding node " + node_id + " to list of nodes to download")
            verboseprint("number of nodes to download: " + str(len(nodes_to_download)))

        diff_for_boundary_cut = filtered_diff
        if len(nodes_to_download) > 0:
            # download list nodes_to_download via overpass, in batches of $node_batches (e.g.12K nodes are rejected by server):
            node_batches = 1000
            node_batch_counter = 0
            overpass_output_array = []
            while node_batch_counter < len(nodes_to_download):
                start_node = node_batch_counter # used for array indexing, starts at 0
                end_node = node_batch_counter + node_batches -1
                if end_node >= len(nodes_to_download) : #we're at the last batch
                    end_node = len(nodes_to_download) -1

                verboseprint("downloading batch of nodes, start=" + str(start_node) + ", end=" + str(end_node) )

                ql = '(\n'

                node_counter = start_node
                while node_counter <= end_node :
                    ql += '  node(' + nodes_to_download[node_counter] + ');\n'
                    node_counter += 1

                ql += ');\n'
                ql += 'out meta;\n' #only mode meta works - osmosis requires version number of elements.

                compact_ql = re.sub(r'(;|\() *', r'\1', ql.replace('\n', ''))
                ql_url = overpass_server_url + compact_ql
                overpass_result = self.__downloadOverpassRetVal(ql_url)
                if overpass_result != "Error" :
                    overpass_output_array.append (overpass_result)

                node_batch_counter += node_batches

            # concatenate outputs into single xml file
            overpass_output = '<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="Overpass API">\n'
            verboseprint("result from download: " + str(len(overpass_output_array)) + " batch(es) of nodes á " + str(node_batches) + " Nodes.")
            for item in overpass_output_array :
                if "<node" in item: #if output not empty (can happen if all nodes are deleted meanwhile)
                    overpass_output_tailcut = item[:-7] # remove last chars ( "</osm>" )
                    overpass_output_headcut = "  <node" + overpass_output_tailcut.split("<node",1)[1]
                    overpass_output += overpass_output_headcut
            overpass_output += "</osm>" #now we have a valid xml file

#            with open("overpass-all.osm", "w") as text_file1:
#                text_file1.write(overpass_output)

            try:
                root = etree.fromstring(overpass_output)
            except:
                #except XMLSyntaxError, e:
                e = sys.exc_info()[0]
                print (e)
                overpass_output = '<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="Overpass API">\n</osm>'
                root = etree.fromstring(overpass_output)

            node_counter = 0
            if root.tag == "osm":
                for item in root:
                    if item.tag == "node":
                        node_counter += 1
                verboseprint("got " + str(node_counter) + " nodes from overpass") #note: overpass API does NOT return deleted nodes!

                # merge overpass node answer with existing
                # note: osmosis does not work, because 2nd input must be a file, and we do not want intermediary files
                # → so concatenate strings: cut off tail of node file and header of diff file.
                overpass_output_tailcut = overpass_output[:-7] # remove last chars ( "</osm>" )
                # find one of the three tags node,way,rel, split on first (assumes that all is in node-way-rel-order)
                diff_with_missing_nodes = filtered_diff
                if "<node" in diff_with_missing_nodes:
                    split_diff = diff_with_missing_nodes.split("<node",1)
                    headcut_diff = "<node" + split_diff[1]
                elif "<way" in diff_with_missing_nodes:   # very unprobable case for no nodes in changeset
                    split_diff = diff_with_missing_nodes.split("<way",1)
                    headcut_diff = "<way" + split_diff[1]
                elif "<relation" in diff_with_missing_nodes: # very very nprobable case for no ways in changeset
                    split_diff = diff_with_missing_nodes.split("<relation",1)
                    headcut_diff = "<relation" + split_diff[1]
                else:
                    print ("Error in changeset split: empty changeset found")
                    headcut_diff = "</osm>"

                diff_for_boundary_cut = overpass_output_tailcut + headcut_diff

            else:
                print ("ERROR, Overpass did not return osm file on missing node download")

        regionfile = os.path.dirname(__file__) + "/vorarlberg.poly"

        args_cutout = ' --read-xml - outPipe.0="osm" \
--bounding-polygon inPipe.0="osm" file="' + regionfile + '" \
--write-xml -'
        self.__content_diff = self.__osmosisCall(args_cutout, diff_for_boundary_cut)

#        with open("diff_cut.osm", "w") as text_file1:
#            text_file1.write(self.__content_diff)

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
            way_count = 0
            rel_count = 0
            for item in root:
                if item.tag == "way":
                    print ('WAY: ' +  item.attrib["id"])
                    print ('  http://www.openstreetmap.org/way/' + item.attrib["id"] + '/history')
                    print ('  http://www.openstreetmap.org/changeset/' + item.attrib["changeset"])
                    way_count += 1
                elif item.tag == "relation":
                    print ('RELATION: ' +  item.attrib["id"])
                    print ('  http://www.openstreetmap.org/relation/' + item.attrib["id"] + '/history')
                    print ('  http://www.openstreetmap.org/changeset/' + item.attrib["changeset"])
                    rel_count += 1
            if way_count == 0 or rel_count == 0:
                    print ('NONE.')
            verboseprint("way count: " + str(way_count) + " , relation count: " + str(rel_count))
        else:
            print ("ERROR: not an osm file")

    def generateRssFeed(self):
        verboseprint("generating rss-item...")
        rssitems = []
        verboseprint("parsing XML...")
        root = etree.fromstring(self.__content_diff)
        rss_description = ""
        max_changeset = -1
        max_changeset_timestamp = ""
        min_changeset = -1
        min_changeset_timestamp = ""
        item_count = 0
        if root.tag == "osm":
            verboseprint("Detected osm file")
            verboseprint("way and relation ids...")
            for item in root:
                if item.tag == "way" or item.tag == "relation":
                    if item.attrib["changeset"] > max_changeset:
                        max_changeset = item.attrib["changeset"]
                        max_changeset_timestamp = item.attrib["timestamp"]
                    if item.attrib["changeset"] < min_changeset or min_changeset == -1:
                        min_changeset = item.attrib["changeset"]
                        min_changeset_timestamp = item.attrib["timestamp"]
                    rss_description += "Modified " + item.tag + ": " + item.attrib["id"] + "<br>"
                    rss_description += '<a href="http://www.openstreetmap.org/' + item.tag + '/' + item.attrib["id"] + '/history">'
                    rss_description += 'http://www.openstreetmap.org/' + item.tag + '/' + item.attrib["id"] + '/history</a><br>'
                    rss_description += '<a href="http://www.openstreetmap.org/changeset/' + item.attrib["changeset"] + '">'
                    rss_description += 'http://www.openstreetmap.org/changeset/' + item.attrib["changeset"] + '</a><br>'
                    item_count += 1
        else:
            print ("ERROR: not an osm file")

        if item_count == 0:
            verboseprint("no rss-items generated (no items exists)")
            return

        rss_title = "Changes between " + min_changeset_timestamp + " and " + max_changeset_timestamp
        rss_link = "http://www.openstreetmap.org/changeset/" + str(max_changeset)
        rssitems.append(PyRSS2Gen.RSSItem(title = rss_title, link = rss_link, description = rss_description))
        rss = PyRSS2Gen.RSS2(
            title = "Regional Diff feed",
            link = "https://github.com/jkirk/osm-regional-diffs",
            description='All modified ways and relations \
from Vorarlberg of the latest minutely replication diff file \
from planet.openstreetmap.org (or by a given diff file)',
            lastBuildDate = datetime.datetime.utcnow(),
            items = rssitems
        )

        self.__appendToRssFile(rss)

    def __appendToRssFile(self, rss):
        if os.path.isfile(args.rss_file):
            verboseprint("append rss-item to existing rss file...")
            rss_temp = tempfile.TemporaryFile()
            rss.write_xml(rss_temp)
            rss_temp.seek(0)
            xml_temp = rss_temp.read()

            root_temp = etree.fromstring(xml_temp)
            appenditem = ""
            channel = root_temp.find("channel")
            appenditem = channel.find("item")

            rss_file = open(args.rss_file, 'rb')

            tree = etree.parse(rss_file)
            rss_root = tree.getroot()
            channel = rss_root.find("channel")
            channel.insert(0, appenditem)

            tree.write(args.rss_file)
        else:
            verboseprint("writing rss-item to new rss file...")
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
        if not self.__ways and not self.__relations:
            self.__content_diff = "<osm></osm>"
        else:
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

