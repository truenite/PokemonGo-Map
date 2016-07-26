#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import logging
from peewee import Model, MySQLDatabase, InsertQuery, IntegerField,\
                   CharField, BooleanField, DateTimeField, DoubleField,\
                   OperationalError

from datetime import datetime
from datetime import timedelta
from base64 import b64encode
from pymysql import MySQLError

from .utils import get_pokemon_name, get_args, load_mysql_credentials
from .transform import transform_from_wgs_to_gcj
from .customLog import printPokemon

from . import config
args = get_args()

credentials = load_mysql_credentials(os.path.dirname(os.path.realpath(__file__)))
if not (credentials['mysql_host'] and  credentials['mysql_port'] and  credentials['mysql_user']
        and  credentials['mysql_pass'] and  credentials['mysql_pass'] and credentials['mysql_db']):
    raise MySQLError(\
        "No MySQl credentials in \config\credentials.json file!")

db = MySQLDatabase(credentials['mysql_db'], host=credentials['mysql_host'],
               port=credentials['mysql_port'], user=credentials['mysql_user'],
               passwd=credentials['mysql_pass'])
log = logging.getLogger(__name__)

class MySQLModel(Model):
    class Meta:
        database = db

    @classmethod
    def get_all(cls):
        results = [m for m in cls.select().dicts()]
        if args.china:
            for result in results:
                result['latitude'],  result['longitude'] = \
                    transform_from_wgs_to_gcj(result['latitude'],  result['longitude'])
        return results

class Search_Location(MySQLModel):
    search_location_id = IntegerField(primary_key=True)
    active = BooleanField()
    parent_id = IntegerField()
    direction_from_parent = CharField()
    step_count = IntegerField()
    latitude = DoubleField()
    longitude = DoubleField()
    account_id = IntegerField()
    running = BooleanField()


class Pokemon(MySQLModel):
    # We are base64 encoding the ids delivered by the api
    # because they are too big for sqlite to handle
    encounter_id = CharField(primary_key=True)
    spawnpoint_id = CharField()
    pokemon_id = IntegerField()
    latitude = DoubleField()
    longitude = DoubleField()
    disappear_time = DateTimeField()
    aprox_found_datetime = DateTimeField()

    @classmethod
    def get_active(cls, swLat, swLng, neLat, neLng):
        if swLat == None or swLng == None or neLat == None or neLng == None:
            query = (Pokemon
                 .select()
                 .where(Pokemon.disappear_time > datetime.utcnow())
                 .dicts())
        else:
            query = (Pokemon
                 .select()
                 .where((Pokemon.disappear_time > datetime.utcnow()) &
                    (Pokemon.latitude >= swLat) &
                    (Pokemon.longitude >= swLng) &
                    (Pokemon.latitude <= neLat) &
                    (Pokemon.longitude <= neLng))
                 .dicts())

        pokemons = []
        for p in query:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
            if args.china:
                p['latitude'], p['longitude'] = \
                    transform_from_wgs_to_gcj(p['latitude'], p['longitude'])
            pokemons.append(p)

        return pokemons

    @classmethod
    def get_active_by_id(cls, ids, swLat, swLng, neLat, neLng):
        if swLat == None or swLng == None or neLat == None or neLng == None:
            query = (Pokemon
                     .select()
                     .where((Pokemon.pokemon_id << ids) &
                            (Pokemon.disappear_time > datetime.utcnow()))
                     .dicts())
        else:
            query = (Pokemon
                     .select()
                     .where((Pokemon.pokemon_id << ids) &
                            (Pokemon.disappear_time > datetime.utcnow()) &
                            (Pokemon.latitude >= swLat) &
                            (Pokemon.longitude >= swLng) &
                            (Pokemon.latitude <= neLat) &
                            (Pokemon.longitude <= neLng))
                     .dicts())

        pokemons = []
        for p in query:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
            if args.china:
                p['latitude'], p['longitude'] = \
                    transform_from_wgs_to_gcj(p['latitude'], p['longitude'])
            pokemons.append(p)

        return pokemons

class Pokestop(MySQLModel):
    pokestop_id = CharField(primary_key=True)
    enabled = BooleanField()
    latitude = DoubleField()
    longitude = DoubleField()
    last_modified = DateTimeField()
    lure_expiration = DateTimeField(null=True)
    active_pokemon_id = IntegerField(null=True)

    @classmethod
    def get_lured():
        query = (Pokestop
                 .select()
                 .where(Pokestop.lure_expiration >> None)
                 .dicts())

        pokestops = []
        for p in query:
            pokestops.append(p)

    @classmethod
    def get_stops(cls, swLat, swLng, neLat, neLng):
        if swLat == None or swLng == None or neLat == None or neLng == None:
            query = (Pokestop
                 .select()
                 .where(Pokestop.lure_expiration != None)
                 .dicts())
        else:
            query = (Pokestop
                 .select()
                 .where((Pokestop.latitude >= swLat) &
                    (Pokestop.longitude >= swLng) &
                    (Pokestop.latitude <= neLat) &
                    (Pokestop.longitude <= neLng)&
                    (Pokestop.lure_expiration != None))
                 .dicts())

        pokestops = []
        for p in query:
            if args.china:
                p['latitude'], p['longitude'] = \
                    transform_from_wgs_to_gcj(p['latitude'], p['longitude'])
            pokestops.append(p)

        return pokestops

        return pokestops

class Gym(MySQLModel):
    UNCONTESTED = 0
    TEAM_MYSTIC = 1
    TEAM_VALOR = 2
    TEAM_INSTINCT = 3

    gym_id = CharField(primary_key=True)
    team_id = IntegerField()
    guard_pokemon_id = IntegerField()
    gym_points = IntegerField()
    enabled = BooleanField()
    latitude = DoubleField()
    longitude = DoubleField()
    last_modified = DateTimeField()

    @classmethod
    def get_gyms(cls, swLat, swLng, neLat, neLng):
        if swLat == None or swLng == None or neLat == None or neLng == None:
            query = (Gym
                 .select()
                 .dicts())
        else:
            query = (Gym
                 .select()
                 .where((Gym.latitude >= swLat) &
                    (Gym.longitude >= swLng) &
                    (Gym.latitude <= neLat) &
                    (Gym.longitude <= neLng))
                 .dicts())

        gyms = []
        for g in query:
            gyms.append(g)

        return gyms


class ScannedLocation(MySQLModel):
    scanned_id = CharField(primary_key=True)
    latitude = DoubleField()
    longitude = DoubleField()
    last_modified = DateTimeField()

    @classmethod
    def get_recent(cls, swLat, swLng, neLat, neLng):
        query = (ScannedLocation
                 .select()
                 .where((ScannedLocation.last_modified >= (datetime.utcnow() - timedelta(minutes=15))) &
                    (ScannedLocation.latitude >= swLat) &
                    (ScannedLocation.longitude >= swLng) &
                    (ScannedLocation.latitude <= neLat) &
                    (ScannedLocation.longitude <= neLng))
                 .dicts())

        scans = []
        for s in query:
            scans.append(s)

        return scans

def parse_map(map_dict, iteration_num, step, step_location):
    pokemons = {}
    pokestops = {}
    gyms = {}
    scanned = {}

    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    for cell in cells:
        for p in cell.get('wild_pokemons', []):
            d_t = datetime.utcfromtimestamp(
                (p['last_modified_timestamp_ms'] +
                 p['time_till_hidden_ms']) / 1000.0)
            printPokemon(p['pokemon_data']['pokemon_id'],p['latitude'],p['longitude'],d_t)
            pokemons[p['encounter_id']] = {
                'encounter_id': b64encode(str(p['encounter_id'])),
                'spawnpoint_id': p['spawnpoint_id'],
                'pokemon_id': p['pokemon_data']['pokemon_id'],
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'disappear_time': d_t,
                'aprox_found_datetime': datetime.utcnow()
            }

        if iteration_num > 0 or step > 50:
            for f in cell.get('forts', []):
                if f.get('type') == 1:  # Pokestops
                        if 'lure_info' in f:
                            lure_expiration = datetime.utcfromtimestamp(
                                f['lure_info']['lure_expires_timestamp_ms'] / 1000.0)
                            active_pokemon_id = f['lure_info']['active_pokemon_id']
                        else:
                            lure_expiration, active_pokemon_id = None, None

                        pokestops[f['id']] = {
                            'pokestop_id': f['id'],
                            'enabled': f['enabled'],
                            'latitude': f['latitude'],
                            'longitude': f['longitude'],
                            'last_modified': datetime.utcfromtimestamp(
                                f['last_modified_timestamp_ms'] / 1000.0),
                            'lure_expiration': lure_expiration,
                            'active_pokemon_id': active_pokemon_id
                    }

                else:  # Currently, there are only stops and gyms
                    gyms[f['id']] = {
                        'gym_id': f['id'],
                        'team_id': f.get('owned_by_team', 0),
                        'guard_pokemon_id': f.get('guard_pokemon_id', 0),
                        'gym_points': f.get('gym_points', 0),
                        'enabled': f['enabled'],
                        'latitude': f['latitude'],
                        'longitude': f['longitude'],
                        'last_modified': datetime.utcfromtimestamp(
                            f['last_modified_timestamp_ms'] / 1000.0),
                    }

    if pokemons:
        log.info("Upserting {} pokemon".format(len(pokemons)))
        bulk_upsert(Pokemon, pokemons)

    if pokestops:
        log.info("Upserting {} pokestops".format(len(pokestops)))
        bulk_upsert(Pokestop, pokestops)

    if gyms:
        log.info("Upserting {} gyms".format(len(gyms)))
        bulk_upsert(Gym, gyms)

    scanned[0] = {
        'scanned_id': str(step_location[0])+','+str(step_location[1]),
        'latitude': step_location[0],
        'longitude': step_location[1],
        'last_modified': datetime.utcnow(),
    }

    bulk_upsert(ScannedLocation, scanned)

def bulk_upsert(cls, data):
    num_rows = len(data.values())
    i = 0
    step = 120

    while i < num_rows:
        log.debug("Inserting items {} to {}".format(i, min(i+step, num_rows)))
        try:
            InsertQuery(cls, rows=data.values()[i:min(i+step, num_rows)]).upsert().execute()
        except OperationalError as e:
            log.warning("%s... Retrying", e)
            continue

        i+=step


def create_tables():
    db.connect()
    db.create_tables([Pokemon, Pokestop, Gym, ScannedLocation], safe=True)
    db.close()
