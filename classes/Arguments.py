#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import time

class Arguments:
    auth_service='ptc'
    username=''
    password=''
    latitude=0
    longitude=0
    step_limit=0
    search_id=0
    no_server=True
    DEBUG=False
    china=False
    cors=False
    db='pogom.db'
    debug=True
    display_in_console=False
    gmaps_key=None
    host='0.0.0.0'
    locale='en'
    mock=False
    port=80
    scan_delay=100
    settings=False
    attempts_to_login=15


    def __init__(self, username, password, latitude, longitude, step_limit, search_id, no_server, mock):
        self.username = username
        self.password = password
        self.latitude = latitude
        self.longitude = longitude
        self.step_limit = step_limit
        self.search_id = search_id
        self.no_server = no_server
        self.mock = mock
