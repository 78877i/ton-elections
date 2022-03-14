from typing import Optional
import inject
from loguru import logger
from pymongo import MongoClient, DESCENDING
from pymongo.database import Database
from webserver import constants

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
def _get_validation_cycles(cycle_id: Optional[str], limit: int, db: Database=None):
    if cycle_id is not None:
        request = {'cycle_id': {'$eq': cycle_id}}
        response = list(db.validation_data.find(request, {'_id': False}))
    else:
        response = list(db.validation_data.find(None, {'_id': False}).limit(limit).sort('cycle_id', DESCENDING))

    for validation_cycle in response:
        election_id = validation_cycle['cycle_id']
        election_req = {'election_id': {'$eq': election_id}}
        election_data = db.elections_data.find_one(election_req)
        if election_data is None:
            logger.error(f"Election entry for cycle_id={election_id} not found!")
            continue

        for validator in validation_cycle['cycle_info']['validators']:
            election_entry = next(participant for participant in election_data['participants_list'] if participant['pubkey'] == validator['pubkey'])
            validator['wallet_address'] = election_entry['wallet_address']
            validator['stake'] = election_entry['stake']
            validator['max_factor'] = election_entry['max_factor']
            complaints_req = {'election_id': {'$eq': election_id},
                              'pubkey': {'$eq': validator['pubkey']}}
            validator['complaints'] = list(db.complaints_data.find(complaints_req, {'_id': False}))

    return response

@inject.autoparams()
def _get_elections(election_id: Optional[int]=None, limit: int=1, db: Database=None):
    if election_id is not None:
        request = {'election_id': {'$eq': election_id}}
        response = list(db.elections_data.find(request, {'_id': False}))
    else:
        response = list(db.elections_data.find(None, {'_id': False}).limit(limit).sort('election_id', DESCENDING))

    for election in response:
        election_id = election['election_id']
        validation_req = {'cycle_id': {'$eq': election_id}}
        validation_cycle = db.validation_data.find_one(validation_req)
        if validation_cycle is None:
            if election['finished']:
                logger.error(f"Validation entry for election_id={election_id} not found!")
            continue

        for participant in election['participants_list']:
            try:
                validation_entry = next(validator for validator in validation_cycle['cycle_info']['validators'] if participant['pubkey'] == validator['pubkey'])
                validator_index = validation_entry['index']
            except StopIteration:
                validator_index = None
            participant['index'] = validator_index

    return response

@inject.autoparams()
def _get_complaints(wallet_address: Optional[str]=None, adnl_address: Optional[str]=None, limit: int=1, db: Database=None):
    request = {}
    if wallet_address is not None:
        request['wallet_address'] = {'$eq': wallet_address}
    if adnl_address is not None:
        request['adnl_addr'] = {'$eq': adnl_address}

    response = list(db.complaints_data.find(request, {'_id': False})
                                      .limit(limit)
                                      .sort([('election_id', DESCENDING), ('created_time', DESCENDING)]))

    return response
