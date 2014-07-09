Regional Diffs
==============

Prerequisites
-------------

`regional-diff.py` has been developed on a Debian/jessie GNU/Linux system and
depends on the following:

* osmosis (0.40.1+ds1-7)
* python (2.7.5-8)

Gettings started
----------------

First clone the repository:

	$ git clone https://github.com/jkirk/osm-regional-diffs.git

View the help message output:

	$ scripts/regional-diff.py --help                                                                                    :(
	usage: regional-diff.py [-h] [-v] [-M | -H | -f FILE | --osmfile OSMFILE]
	                        [--report | --ids-only | --ql-only | --rss-file RSS_FILE]
	
	Print report of all modified ways and relations from Vorarlberg of the latest minutely or hourly replication diff file from planet.openstreetmap.org (or by a given diff file)
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -v, --verbose         increase verbosity
	  -M, --minutely        use minutely diff file from planet.openstreetmap.org
	                        (default)
	  -H, --hourly          use hourly diff file from planet.openstreetmap.org
	  -f FILE, --file FILE  use local osc.gz diff file (instead of downloading the
	                        latest diff file from planet.openstreetmap.org)
	  --osmfile OSMFILE     use local osm file (from osmosis or overpass API)
	  --report              output report to stdout (default)
	  --ids-only            output all way and relation IDs from given diff
	  --ql-only             output Overpass QL
	  --rss-file RSS_FILE   output report as rss file

`regional-diff.py` by default reports ways and relations with bicylce-tags[1] in
Vorarlberg which were modified in the last minute.

As it is very likely that there haven't been any changes in the last minute it
might make sense to test `regional-diff.py` with changes done in the last hour
or by providing a diff file. To do so run either:

	$ scripts/regional-diff.py --hourly

or 

	$ scripts/regional-diff.py -f scripts/637.osc.gz

`637.osc.gz` was downloaded from
http://planet.openstreetmap.org/replication/hour/000/015/637.osc.gz which was
created on `#Wed Jun 25 20:02:07 UTC 2014`. This should be the sample output:

	The following ways and relations (in Vorarlberg) have been modified in scripts/637.osc.gz
	WAY: 69998530
	  http://www.openstreetmap.org/way/69998530/history
	  http://www.openstreetmap.org/changeset/23158682
	WAY: 118905057
	  http://www.openstreetmap.org/way/118905057/history
	  http://www.openstreetmap.org/changeset/23158682
	WAY: 289794459
	  http://www.openstreetmap.org/way/289794459/history
	  http://www.openstreetmap.org/changeset/23158682
	WAY: 289794460
	  http://www.openstreetmap.org/way/289794460/history
	  http://www.openstreetmap.org/changeset/23158682
	WAY: 289794461
	  http://www.openstreetmap.org/way/289794461/history
	  http://www.openstreetmap.org/changeset/23158682
	RELATION: 13132
	  http://www.openstreetmap.org/relation/13132/history
	  http://www.openstreetmap.org/changeset/24003836
	RELATION: 116941
	  http://www.openstreetmap.org/relation/116941/history
	  http://www.openstreetmap.org/changeset/23158682	

To generate an RSS-file run:

	$ scripts/regional-diff.py -f scripts/637.osc.gz --rss-file regional-diff.rss

Put the RSS-file to your `htdocs` folder and point your favourite RSS-Client to that URL to subscribe that feed.

Please be aware that the RSS-File will be overwriten on every run of `regional-diff.py`

