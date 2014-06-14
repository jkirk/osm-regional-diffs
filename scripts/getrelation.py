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
    __is_part_of_ul = False
    __is_part_of_ul_a = False

    def handle_starttag(self, tag, attrs):
        if tag == "h4":
            self.__is_part_of = False
            self.__is_h4 = True
        if tag == "ul":
            if self.__is_part_of:
                self.__is_part_of_ul = True
        if tag == "a" and self.__is_part_of_ul:
            self.__is_part_of_ul_a = True
            for attr in attrs:
                print attr[1]
    def handle_endtag(self, tag):
        if tag == "h4":
            self.__is_h4 = False
        if tag == "ul":
            self.__is_part_of_ul = False
        if tag == "a" and self.__is_part_of_ul:
            self.__is_part_of_ul_a = False

    def handle_data(self, data):
        if self.__is_h4:
            if data == "Part of":
                self.__is_part_of = True

response = urllib2.urlopen("http://www.openstreetmap.org/way/30245439")
waycontent = response.read()

parser = PartOfParser()
parser.feed(waycontent)

