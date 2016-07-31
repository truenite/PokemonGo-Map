#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import time
import multiprocessing
import subprocess
import socket
import logging
import signal
from threading import Thread
from PokemonDAL import Arguments, models
from PokemonDAL.models import Pokemon, Pokestop, Gym, Search_Location, PCAccount, Step_Distance
from PokemonFinder.search import search_loop
from PokemonFinder.pgoapi import *
from importlib import import_module

running_threads = []
running_processes = []
stoping=0

def close_app(signal, frame):
    global running_processes
    stoping=1
    log.info('Terminating.')
    query = Search_Location.update(running=0,pid=-1)
    query.execute()
    for x in range(0, 1):
        for rp in running_processes:
            if(rp.is_alive() == True):
                running_processes.remove(rp)
                rp.terminate()
            time.sleep(10)
    os._exit(0)

def check_for_dead_processes():
    global running_processes
    if stoping==0:
        for rp in running_processes:
            if(rp.is_alive() == False):
                if(rp.name=="0"):
                    start_web()
                else:
                    log.debug("Proceso {:d} con searchId {:s} estaba muerto".format(rp.pid,rp.name))
                    s = Search_Location.get(Search_Location.search_location_id == rp.name)
                    s.running=0
                    s.pid = -1
                    s.save()
                    running_processes.remove(rp)

def add_and_start_process(args):
    global running_processes
    process = multiprocessing.Process(name=''+str(args.search_id), target=search_loop, args=(args,True,))
    process.start()
    running_processes.append(process)
    log.info("Starting '%s' - '%s'", process.name, process.pid)
    sys.stdout.flush()

def get_coordenates_for_search(parent_id,direction,step_count,search_id):
    step_distance = Step_Distance.select().where(Step_Distance.step_count == step_count).get()
    parent_location = Search_Location.get(Search_Location.search_location_id == parent_id)
    location = []
    if(direction=="N"):
        location = [parent_location.latitude + step_distance.diff_lat, parent_location.longitude]
    if(direction=="NE"):
        location = [parent_location.latitude + step_distance.diff_lat / 2 , parent_location.longitude + step_distance.diff_lon * 3 / 4]
    if(direction=="E"):
        location = [parent_location.latitude , parent_location.longitude + step_distance.diff_lon * 1.5]
    if(direction=="SE"):
        location = [parent_location.latitude - step_distance.diff_lat / 2 , parent_location.longitude + step_distance.diff_lon * 3 / 4]
    if(direction=="S"):
        location = [parent_location.latitude - step_distance.diff_lat , parent_location.longitude]
    if(direction=="SW"):
        location = [parent_location.latitude - step_distance.diff_lat / 2 , parent_location.longitude - step_distance.diff_lon * 3 / 4]
    if(direction=="W"):
        location = [parent_location.latitude , parent_location.longitude - step_distance.diff_lon * 1.5]
    if(direction=="NW"):
        location = [parent_location.latitude + step_distance.diff_lat / 2 , parent_location.longitude - step_distance.diff_lon * 3 / 4]

    actual_location = Search_Location.get(Search_Location.search_location_id == search_id)
    actual_location.latitude = location[0]
    actual_location.longitude = location[1]
    actual_location.save()

    return location

def get_python_command(pending_search):
    account = PCAccount.get(PCAccount.pcaccount_id == pending_search["account_id"])

    if(pending_search["parent_id"]==-1):
        coordinates = [pending_search["latitude"],pending_search["longitude"]]
    else:
        coordinates = get_coordenates_for_search(pending_search["parent_id"],
         pending_search["direction_from_parent"], pending_search["step_count"], pending_search["search_location_id"])

    args = Arguments(account.username, account.password, coordinates[0], coordinates[1], pending_search["step_count"], pending_search["search_location_id"], True, False)

    return args

log = logging.getLogger("startSearch")
logLevel = logging.ERROR
logging.basicConfig(level=logLevel, format='%(asctime)s [%(module)11s] [%(levelname)7s] %(message)s')

if __name__ == "__main__":
    logging.getLogger("peewee").setLevel(logLevel)
    logging.getLogger("requests").setLevel(logLevel)
    logging.getLogger("pogom.pgoapi.pgoapi").setLevel(logLevel)
    logging.getLogger("pogom.pgoapi.rpc_api").setLevel(logLevel)
    logging.getLogger("search").setLevel(logLevel)
    logging.getLogger("models").setLevel(logLevel)

    signal.signal(signal.SIGINT, close_app)
    while(True):
        pending_searches = Search_Location.get_not_running()
        for ps in pending_searches:
            args = get_python_command(ps)
            add_and_start_process(args)
            time.sleep(1)
        check_for_dead_processes()
        time.sleep(1)
