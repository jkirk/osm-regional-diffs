#!/usr/bin/python

import argparse, urllib, urllib2, re, gzip, subprocess, os, sys, shlex
from lxml import etree
from HTMLParser import HTMLParser

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        print "Encountered a start tag:", tag
    def handle_endtag(self, tag):
        print "Encountered an end tag :", tag
    def handle_data(self, data):
        print "Encountered some data  :", data

class PartOfParser(HTMLParser):
    __is_h4 = False
    __is_part_of = False

    def handle_starttag(self, tag, attrs):
        if tag == "h4":
            self.__is_h4 = True
            print "Encountered a start tag:", tag
    def handle_endtag(self, tag):
        if tag == "h4":
            self.__is_h4 = False
            print "Encountered an end tag :", tag
    def handle_data(self, data):
        if self.__is_h4:
            if data == "Part of":
                print data

response = urllib2.urlopen("http://www.openstreetmap.org/way/30245439")
waycontent = response.read()

parser = PartOfParser()
parser.feed(waycontent)

