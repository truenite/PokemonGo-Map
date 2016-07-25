#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import json
import logging
from peewee import Model, MySQLDatabase, InsertQuery, IntegerField,\
                   CharField, BooleanField, DateTimeField, DoubleField

from pymysql import MySQLError

def load_mysql_credentials(filepath):
    try:
        with open(filepath+os.path.sep+'../PokemonGoMap/config/credentials.json') as file:
            creds = json.load(file)
    except IOError:
        creds = {}
    return creds

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

class Step_Distance(MySQLModel):
    step_id = IntegerField(primary_key=True)
    step_count = IntegerField()
    diff_lat = DoubleField()
    diff_lon = DoubleField()

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

    @classmethod
    def get_not_running(cls):
        query = (Search_Location
                 .select()
                 .where(Search_Location.active == 1, Search_Location.running == 0)
                 .dicts())

        locations = []
        for l in query:
            locations.append(l)
        return locations

class PCAccount(MySQLModel):
    pcaccount_id = IntegerField(primary_key=True)
    username = CharField()
    password = CharField()


def bulk_upsert(cls, data):
    num_rows = len(data.values())
    i = 0
    step = 120

    while i < num_rows:
        log.debug("Inserting items {} to {}".format(i, min(i+step, num_rows)))
        InsertQuery(cls, rows=data.values()[i:min(i+step, num_rows)]).upsert().execute()
        i+=step
