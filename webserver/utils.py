from typing import Optional, List
from collections import defaultdict

import inject

from pymongo import MongoClient, DESCENDING
from pymongo.database import Database
from webserver import constants

from loguru import logger


# inject configure
def inject_config(binder):
    with open(constants.MONGO_PASSWORD_FILE, 'r') as f:
        password = f.read()
    client = MongoClient(host=constants.MONGO_HOST, 
                         port=constants.MONGO_PORT,
                         username=constants.MONGO_USER,
                         password=password)
    db_name = constants.MONGO_DATABASE
    binder.bind(Database, client[db_name])

inject.configure_once(inject_config)


@inject.autoparams()
def _get_validation_cycle_ids_by_limit(limit: int, db: Database):
    cycle_ids_pipeline = [
        {"$sort": {'cycle_id': -1}},
        {"$limit": limit},
        {"$project": {"cycle_id": 1}}
    ]

    cycle_ids = list(x['cycle_id'] for x in db.validation_data.aggregate(cycle_ids_pipeline))
    return cycle_ids


@inject.autoparams()
def _get_validation_cycle_ids_by_wallet_address(wallet_address: Optional[str],
                                                limit: int,
                                                db: Database):

    pubkey_pipeline = [
        {"$unwind": "$participants_list"},
        {"$match": {"participants_list.wallet_address": wallet_address}},
        {"$group": {"_id": wallet_address, "pubkey": {"$addToSet": "$participants_list.pubkey"}}},
    ]
    pubkey_list = list(db.elections_data.aggregate(pubkey_pipeline))[0]['pubkey']

    cycle_ids_pipeline = [
        {"$unwind":"$cycle_info.validators"},
        {"$match": {"cycle_info.validators.pubkey": {"$in": pubkey_list}}},
        {"$sort": {'cycle_id': -1}},
        {"$limit": limit},
        {"$project": {"cycle_id": 1}}
    ]

    cycle_ids = list(x['cycle_id'] for x in db.validation_data.aggregate(cycle_ids_pipeline))
    return cycle_ids


@inject.autoparams()
def _get_validation_cycle_ids_by_adnl_address(adnl_addr: Optional[str],
                                              limit: int,
                                              db: Database):

    cycle_ids_pipeline = [
        {"$unwind":"$cycle_info.validators"},
        {"$match": {"cycle_info.validators.adnl_addr": adnl_addr}},
        {"$sort": {'cycle_id': -1}},
        {"$limit": limit},
        {"$project": {"cycle_id": 1}}
    ]

    cycle_ids = list(x['cycle_id'] for x in db.validation_data.aggregate(cycle_ids_pipeline))
    return cycle_ids


@inject.autoparams()
def _get_validation_cycles(cycle_id: Optional[int]=None, 
                           wallet_address: Optional[str]=None,
                           adnl_address: Optional[str]=None,
                           limit: int=1,
                           return_participants: bool=True, 
                           db: Database=None):
    if cycle_id or wallet_address or adnl_address:
        by_cycle_id, by_wallet_address, by_adnl_address = None, None, None
        if cycle_id is not None:
            by_cycle_id = [cycle_id]
        if wallet_address is not None:
            by_wallet_address = _get_validation_cycle_ids_by_wallet_address(wallet_address, limit)
        if adnl_address is not None:
            by_adnl_address = _get_validation_cycle_ids_by_adnl_address(adnl_address, limit)

        # find intersection of arrays by_cycle_id, by_wallet_address, by_adnl_address but ignore None
        cycle_ids = list(set.intersection(*map(set, filter(lambda x: x is not None, [by_cycle_id, by_wallet_address, by_adnl_address]))))
    else:
        cycle_ids = _get_validation_cycle_ids_by_limit(limit)

    pipeline = [
        {"$match": {"cycle_id": {"$in": cycle_ids}}},
        {"$lookup": {
            "from": "elections_data",
            "localField": "cycle_id",
            "foreignField": "election_id",
            "as": "election_info"
        }},
        {"$lookup": {
            "from": "complaints_data",
            "localField": "cycle_id",
            "foreignField": "election_id",
            "as": "complaints_list"
        }},
        {"$sort": {"cycle_id": -1}}
    ]

    result = list(db.validation_data.aggregate(pipeline))
    for rec in result:
        if not (len(rec['election_info']) == 1):
            logger.warning(f"More than one election_info found")

        complaints_dict = defaultdict(list)
        for comp in rec.pop('complaints_list'):
            comp.pop('_id')
            complaints_dict[comp['pubkey']].append(comp)

        elections_dict = rec.pop('election_info')[0]['participants_list']
        elections_dict = {x['pubkey']: x for x in elections_dict}

        if not return_participants:
            if wallet_address or adnl_address:
                # leave only requested participant in `validators` array
                if wallet_address:
                    rec['cycle_info']['validators'] = filter(lambda x: x['wallet_address'] == wallet_address, rec['cycle_info']['validators'])
                if adnl_address:
                    rec['cycle_info']['validators'] = filter(lambda x: x['adnl_address'] == adnl_address, rec['cycle_info']['validators'])
            else:
                rec['cycle_info']['validators'] = []

        for val in rec['cycle_info']['validators']:
            elect = elections_dict[val['pubkey']]
            if not (val['adnl_addr'] == elect['adnl_addr']):
                logger.warning(f"Election info: adnl_addr mismatch")
            val.update(elect)

            val['complaints'] = complaints_dict[val['pubkey']]

        rec.pop('_id')
    return result


@inject.autoparams()
def _get_elections(election_id: Optional[int]=None, 
                   wallet_address: Optional[str]=None,
                   adnl_address: Optional[str]=None, 
                   limit: int=1, 
                   return_participants: bool=True, 
                   db: Database=None):
    request = {}
    if election_id is not None:
        request['election_id'] = {'$eq': election_id}
    if wallet_address is not None:
        request['participants_list.wallet_address'] = {'$eq': wallet_address}
    if adnl_address is not None:
        request['participants_list.adnl_addr'] = {'$eq': adnl_address}

    response = list(db.elections_data.find(request, {'_id': False}).limit(limit).sort('election_id', DESCENDING))

    for election in response:
        election_id = election['election_id']
        validation_req = {'cycle_id': {'$eq': election_id}}
        validation_cycle = db.validation_data.find_one(validation_req)
        if validation_cycle is None:
            if election['finished']:
                logger.error(f"Validation entry for election_id={election_id} not found!")
            continue

        election['total_participants'] = len(election['participants_list'])

        if not return_participants:
            # leave only requested participant in `participants_list` array
            if wallet_address or adnl_address:
                if wallet_address:
                    election['participants_list'] = filter(lambda x: x['wallet_address'] == wallet_address, election['participants_list'])
                if adnl_address:
                    election['participants_list'] = filter(lambda x: x['adnl_address'] == adnl_address, election['participants_list'])
            else:
                election['participants_list'] = []


        for participant in election['participants_list']:
            try:
                validation_entry = next(validator for validator in validation_cycle['cycle_info']['validators'] if participant['pubkey'] == validator['pubkey'])
                validator_index = validation_entry['index']
            except StopIteration:
                validator_index = None
            participant['index'] = validator_index

    return response


@inject.autoparams()
def _get_complaints(wallet_address: Optional[str]=None, 
                    adnl_address: Optional[str]=None, 
                    election_id: Optional[int]=None, 
                    limit: int=1, 
                    db: Database=None):
    request = {}
    if wallet_address is not None:
        request['wallet_address'] = {'$eq': wallet_address}
    if adnl_address is not None:
        request['adnl_addr'] = {'$eq': adnl_address}
    if election_id is not None:
        request['election_id'] = {'$eq': election_id}

    response = list(db.complaints_data.find(request, {'_id': False})
                                      .limit(limit)
                                      .sort([('election_id', DESCENDING), ('created_time', DESCENDING)]))

    return response
