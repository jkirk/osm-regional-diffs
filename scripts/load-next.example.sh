#!/bin/bash
# loads the diffs for the interval read from configuration.txt
# may be executed every 5 minutes or so

PIDFILE=`basename $0`.pid

OSMOSIS=/usr/bin/osmosis
OSM2PGSQL=/usr/bin/osm2pgsql
STYLE=/usr/share/osm2pgsql/default.style

HSTORE="" # disable hstore, as not supported on debian osm2pgsql
HSTORE="--hstore"
PSQ_BBOX="--bbox 9.5,46.3,17.2,49" #bbox for AT import
PSQ_BBOX="--bbox 5.5,42,20,56" #bbox for AT-DE-HR
#PSQ_BBOX="" # try osmosis bbox instead
#OSM_BBOX="--bounding-box top=49 left=9.5 bottom=46.3 right=17.2"

O2PGS_ARGS="--number-processes 6"

# java proxy settings for osmosis
#JAVACMD_OPTIONS="-Dhttp.proxyHost=ha-proxy.esi -Dhttp.proxyPort=8080"
#export JAVACMD_OPTIONS
JAVACMD_OPTIONS="-server"
export JAVACMD_OPTIONS

OSMOSISLOG=/var/log/osm/osmosis.log
PSQLLOG=/var/log/osm/osm2pgsql.log
RUNLOG=/var/log/osm/load-next.log

HOST=/var/run/postgresql
DB=gis
PREFIX=planet_osm
USER=gis

CURRENT=/tmp/osm-load-next.$$.osc
EXPIRE=0

m_info()
{
	echo "[`date +"%Y-%m-%d %H:%M:%S"`] $$ $1" >> "$RUNLOG"
}

m_error()
{
	echo "[`date +"%Y-%m-%d %H:%M:%S"`] $$ [error] $1" >> "$RUNLOG"
	
	m_info "resetting state"
	/bin/cp last.state.txt state.txt
	
	rm "$PIDFILE"
	exit 1
}

m_ok()
{
	echo "[`date +"%Y-%m-%d %H:%M:%S"`] $$ $1" >> "$RUNLOG"
}

getlock()
{
	if [ -s $PIDFILE ]; then
		if [ "$(ps -p `cat $PIDFILE` | wc -l)" -gt 1 ]; then
			return 1 #false
		fi
	fi
	
	echo $$ >"$PIDFILE"
	return 0 #true
}

freelock()
{
	rm "$PIDFILE"
}

WDIR=`dirname $0`
pushd $WDIR >/dev/null
#m_info "Workingdir $WDIR"

if ! getlock; then
	m_info "pid `cat $PIDFILE` still running"
	exit 3
fi

if [ -e stop -o -e stop.txt ]; then
	m_info "stopped"
	exit 2
fi

#by MM
/usr/sbin/logrotate -v -f /etc/logrotate.d/osm-load-next 1>&2 2> /var/log/osm/logrotate.log

m_ok "start import"
echo $$ >"$PIDFILE"

/bin/cp state.txt last.state.txt
m_ok "downloading diff"
if ! $OSMOSIS --read-replication-interval --simplify-change --write-xml-change "$CURRENT" 1>&2 2> "$OSMOSISLOG"; then
	m_error "osmosis error"
fi

NODES=`grep '<node' < "$CURRENT" |wc -l`
WAYS=`grep '<way' < "$CURRENT" |wc -l`
RELS=`grep '<rel' < "$CURRENT" |wc -l`

m_info "expecting Node("$((NODES / 1000))"k) Way("$((WAYS / 1000))"k) Relation("$((RELS / 1000))"k)"

m_ok "importing diff"
if ! $OSM2PGSQL --append --slim --cache 2024 $PSQ_BBOX --merc --prefix $PREFIX --style $STYLE --host $HOST --database $DB --username $USER $HSTORE $O2PGS_ARGS --verbose "$CURRENT" 1> /dev/null 2> "$PSQLLOG"; then
	m_error "osm2pgsql error"
fi

m_ok "import done"
freelock

