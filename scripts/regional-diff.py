#!/usr/bin/python

import argparse

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

if __name__ == '__main__':
    print "Currently no action"

