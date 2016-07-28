#!/usr/bin/python
# -*- coding: utf-8 -*-

def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string
