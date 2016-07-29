#!/usr/bin/python
# -*- coding: utf-8 -*-
import calendar
import logging
import sys
import os

from flask import Flask, jsonify, render_template, request
from flask.json import JSONEncoder
from flask_compress import Compress
from datetime import datetime
from s2sphere import *
from flask_cors import CORS, cross_origin

sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/../PokemonDAL/')
from models import *
from . import config

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                if obj.utcoffset() is not None:
                    obj = obj - obj.utcoffset()
                millis = int(
                    calendar.timegm(obj.timetuple()) * 1000 +
                    obj.microsecond / 1000
                )
                return millis
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

log = logging.getLogger(__name__)
app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
compress = Compress()
compress.init_app(app)
CORS(app)

@app.route("/", methods=['GET'])
def fullmap():
    display = "inline"
    return render_template('map.html',
                           lat=config['ORIGINAL_LATITUDE'],
                           lng=config['ORIGINAL_LONGITUDE'],
                           gmaps_key=config['GMAPS_KEY'],
                           lang=config['LOCALE'],
                           is_fixed=display
                           )

@app.route('/zonasEscaneadas', methods=['GET'])
def fullmap_with_scan():
    display = "inline"
    return render_template('map_with_scan.html',
                           lat=config['ORIGINAL_LATITUDE'],
                           lng=config['ORIGINAL_LONGITUDE'],
                           gmaps_key=config['GMAPS_KEY'],
                           lang=config['LOCALE'],
                           is_fixed=display
                           )

@app.route("/raw_data", methods=['GET'])
def raw_data():
    d = {}
    swLat = request.args.get('swLat')
    swLng = request.args.get('swLng')
    neLat = request.args.get('neLat')
    neLng = request.args.get('neLng')
    if request.args.get('pokemon', 'true') == 'true':
        if request.args.get('ids'):
            ids = [int(x) for x in request.args.get('ids').split(',')]
            print("ENTRO")
            d['pokemons'] = Pokemon.get_active_by_id(ids, swLat, swLng, neLat, neLng)
        else:
            d['pokemons'] = Pokemon.get_active(swLat, swLng, neLat, neLng)

    if request.args.get('pokestops', 'false') == 'true':
        d['pokestops'] = Pokestop.get_stops(swLat, swLng, neLat, neLng)

    if request.args.get('gyms', 'true') == 'true':
        d['gyms'] = Gym.get_gyms(swLat, swLng, neLat, neLng)

    return jsonify(d)

@app.route("/raw_data_with_scan", methods=['GET'])
def raw_data_with_scan():
    d = {}
    swLat = request.args.get('swLat')
    swLng = request.args.get('swLng')
    neLat = request.args.get('neLat')
    neLng = request.args.get('neLng')
    if request.args.get('pokemon', 'true') == 'true':
        if request.args.get('ids'):
            ids = [int(x) for x in request.args.get('ids').split(',')]
            d['pokemons'] = Pokemon.get_active_by_id(ids, swLat, swLng, neLat, neLng)
        else:
            d['pokemons'] = Pokemon.get_active(swLat, swLng, neLat, neLng)

    if request.args.get('pokestops', 'false') == 'true':
        d['pokestops'] = Pokestop.get_stops(swLat, swLng, neLat, neLng)

    if request.args.get('gyms', 'true') == 'true':
        d['gyms'] = Gym.get_gyms(swLat, swLng, neLat, neLng)
    if request.args.get('scanned', 'true') == 'true':
        d['scanned'] = ScannedLocation.get_recent(swLat, swLng, neLat, neLng)
    return jsonify(d)

@app.route("/mobile", methods=['GET'])
def list_pokemon():
    # todo: check if client is android/iOS/Desktop for geolink, currently only supports android
    pokemon_list = []

    # Allow client to specify location
    lat = request.args.get('lat', config['ORIGINAL_LATITUDE'], type=float)
    lon = request.args.get('lon', config['ORIGINAL_LONGITUDE'], type=float)
    origin_point = LatLng.from_degrees(lat, lon)

    for pokemon in Pokemon.get_active(None, None, None, None):
        pokemon_point = LatLng.from_degrees(pokemon['latitude'], pokemon['longitude'])
        diff = pokemon_point - origin_point
        diff_lat = diff.lat().degrees
        diff_lng = diff.lng().degrees
        direction = (('N' if diff_lat >= 0 else 'S') if abs(diff_lat) > 1e-4 else '') + (
            ('E' if diff_lng >= 0 else 'W') if abs(diff_lng) > 1e-4 else '')
        entry = {
           'id': pokemon['pokemon_id'],
            'name': pokemon['pokemon_name'],
            'card_dir': direction,
            'distance': int(origin_point.get_distance(pokemon_point).radians * 6366468.241830914),
            'time_to_disappear': '%d min %d sec' % (divmod((pokemon['disappear_time']-datetime.utcnow()).seconds, 60)),
            'disappear_time': pokemon['disappear_time'],
            'latitude': pokemon['latitude'],
            'longitude': pokemon['longitude']
        }
        pokemon_list.append((entry, entry['distance']))
    pokemon_list = [y[0] for y in sorted(pokemon_list, key=lambda x: x[1])]
    return render_template('mobile_list.html',
                           pokemon_list=pokemon_list,
                           origin_lat=lat,
                           origin_lng=lon)
