#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time
import math
import sys
import psutil
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/../PokemonDAL/')
from models import Search_Location, parse_map

from pgoapi import PGoApi
from pgoapi.utilities import f2i, get_cellid
from pgoapi.utilities import get_pos_by_name

from . import config

log = logging.getLogger(__name__)

TIMESTAMP = '\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000'
api = PGoApi()

def calculate_lng_degrees(lat):
    return float(lng_gap_meters) / \
        (meters_per_degree * math.cos(math.radians(lat)))


def send_map_request(api, position):
    try:
        api.set_position(*position)
        api.get_map_objects(latitude=f2i(position[0]),
                                 longitude=f2i(position[1]),
                                 since_timestamp_ms=TIMESTAMP,
                                 cell_id=get_cellid(position[0], position[1]))
        return api.call()
    except Exception as e:
        log.warning("Uncaught exception when downloading map " + str(e))
        return False

def get_new_coords(init_loc, distance, bearing):
    """ Given an initial lat/lng, a distance(in kms), and a bearing (degrees),
    this will calculate the resulting lat/lng coordinates.
    """
    R = 6378.1 #km radius of the earth
    bearing = math.radians(bearing)

    init_coords = [math.radians(init_loc[0]), math.radians(init_loc[1])] # convert lat/lng to radians

    new_lat = math.asin( math.sin(init_coords[0])*math.cos(distance/R) +
        math.cos(init_coords[0])*math.sin(distance/R)*math.cos(bearing))

    new_lon = init_coords[1] + math.atan2(math.sin(bearing)*math.sin(distance/R)*math.cos(init_coords[0]),
        math.cos(distance/R)-math.sin(init_coords[0])*math.sin(new_lat))

    return [math.degrees(new_lat), math.degrees(new_lon)]

def generate_location_steps(initial_loc, step_count):
    #Bearing (degrees)
    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270

    pulse_radius = 0.1                  # km - radius of players heartbeat is 100m
    xdist = math.sqrt(3)*pulse_radius   # dist between column centers
    ydist = 3*(pulse_radius/2)          # dist between row centers

    yield (initial_loc[0], initial_loc[1], 0) #insert initial location

    ring = 1
    loc = initial_loc
    while ring < step_count:
        #Set loc to start at top left
        loc = get_new_coords(loc, ydist, NORTH)
        loc = get_new_coords(loc, xdist/2, WEST)
        for direction in range(6):
            for i in range(ring):
                if direction == 0: # RIGHT
                    loc = get_new_coords(loc, xdist, EAST)
                if direction == 1: # DOWN + RIGHT
                    loc = get_new_coords(loc, ydist, SOUTH)
                    loc = get_new_coords(loc, xdist/2, EAST)
                if direction == 2: # DOWN + LEFT
                    loc = get_new_coords(loc, ydist, SOUTH)
                    loc = get_new_coords(loc, xdist/2, WEST)
                if direction == 3: # LEFT
                    loc = get_new_coords(loc, xdist, WEST)
                if direction == 4: # UP + LEFT
                    loc = get_new_coords(loc, ydist, NORTH)
                    loc = get_new_coords(loc, xdist/2, WEST)
                if direction == 5: # UP + RIGHT
                    loc = get_new_coords(loc, ydist, NORTH)
                    loc = get_new_coords(loc, xdist/2, EAST)
                yield (loc[0], loc[1], 0)
        ring += 1


def login(args, position):
    log.info('Attempting login to Pokemon Go.')
    api.set_position(*position)

    attempts = 0
    while not api.login(args.auth_service, args.username, args.password):
        log.info('Failed to login to Pokemon Go. Trying again.')
        if(attempts >= args.attempts_to_login):
            log.error('Killing process {:d} - Too much login errors'.format(os.getpid()))
            os._exit(1)
        attempts=attempts+1

    log.info('Login to Pokemon Go successful.')

def search(args, i):
    num_steps = args.step_limit
    position = (config['ORIGINAL_LATITUDE'], config['ORIGINAL_LONGITUDE'], 0)

    if api._auth_provider and api._auth_provider._ticket_expire:
        remaining_time = api._auth_provider._ticket_expire/1000 - time.time()
        if remaining_time > 60:
            log.info("Skipping Pokemon Go login process since already logged in for another {:.2f} seconds".format(remaining_time))
        else:
            login(args, position)
    else:
        login(args, position)

    for step, step_location in enumerate(generate_location_steps(position, num_steps), 1):
        log.debug('Scan location is {:f}, {:f}'.format(step_location[0], step_location[1]))

        response_dict = {}
        failed_consecutive = 0
        while not response_dict:
            response_dict = send_map_request(api, step_location)
            if (response_dict and any(response_dict["responses"])):
                try:
                    parse_map(response_dict, i, step, step_location, args.search_id)
                    time.sleep(.205)
                except KeyError:
                    log.error('Scan step {:d} failed. Response dictionary key error. - Process : {:d} - SearchId {:d}'.format(os.getpid(), args.search_id))
                    failed_consecutive += 1
                    if(failed_consecutive >= config['ERRORS_BEFORE_SLEEP']):
                        log.error('Niantic servers under heavy load. Waiting before trying again')
                        time.sleep(config['SLEEP_FOR_AFTER_FAILED'])
                        failed_consecutive = 0
            else:
                log.error('Empty response from API, retrying. - Process : {:d} - SearchId {:d}'.format(os.getpid(), args.search_id))

def search_loop(args,parseLocationFromArg = False):
    i = 0
    config['LOCALE'] = args.locale

    if(parseLocationFromArg==True):
        config['ORIGINAL_LATITUDE'] = args.latitude
        config['ORIGINAL_LONGITUDE'] = args.longitude
        config['SEARCH_ID'] = args.search_id

    search_location = Search_Location.get(Search_Location.search_location_id == args.search_id)
    search_location.running = 1
    search_location.save()

    try:
        while True:
            log.info("Map iteration: {}".format(i))
            search(args, i)
            log.info("Scanning complete.")
            if args.scan_delay > 1:
                log.info('Waiting {:d} seconds before beginning new scan.'.format(args.scan_delay))
            i += 1

    # This seems appropriate
    except:
        log.debug('Crashed, waiting {:d} seconds before restarting search.'.format(args.scan_delay))
        time.sleep(args.scan_delay)
        search_loop(args, True)
