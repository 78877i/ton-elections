from datetime import datetime
from pymongo import MongoClient
from indexer.celery import app
from indexer.liteclient import LiteClient, LiteClientException
from indexer.utils import Dec2HexAddr, HexAddr2Base64Addr

import indexer.constants as constants

lite_client = LiteClient(constants.LITE_CLIENT_BINARY, constants.LITE_CLIENT_CONFIG)

@app.task(autoretry_for=(LiteClientException,), default_retry_delay=1, max_retries=5)
def update_validation_cycle():
    with open(constants.MONGO_PASSWORD_FILE, 'r') as f:
        password = f.read()
    client = MongoClient(host=constants.MONGO_HOST, 
                         port=constants.MONGO_PORT,
                         username=constants.MONGO_USER,
                         password=password)
    validation_collection = client[constants.MONGO_DATABASE]['validation_data']
    validation_collection.create_index('cycle_id')

    validators = lite_client.get_validators_list(36)

    if not validators:
        return 'Config 36 is not ready yet'

    prev_saved_config = validation_collection.find_one({
        'cycle_id': {
            '$eq' : validators['utime_since']
        }
    })
    if prev_saved_config is not None:
        if prev_saved_config['cycle_info'] == validators:
            return 'Validators config did not change'

    config15 = lite_client.get_config(15)
    config16 = lite_client.get_config(16)
    config17 = lite_client.get_config_17()
    
    data = {
        'cycle_id': validators['utime_since'],
        'cycle_info': validators,
        'config15': config15,
        'config16': config16,
        'config17': config17
    }

    validation_collection.replace_one({'cycle_id' : {'$eq': validators['utime_since']}}, data, upsert=True)

    return 'Validators config updated'

@app.task(autoretry_for=(LiteClientException,), default_retry_delay=1, max_retries=5)
def update_elections():
    with open(constants.MONGO_PASSWORD_FILE, 'r') as f:
        password = f.read()
    client = MongoClient(host=constants.MONGO_HOST, 
                         port=constants.MONGO_PORT,
                         username=constants.MONGO_USER,
                         password=password)
    elections_collection = client[constants.MONGO_DATABASE]['elections_data']
    elections_collection.create_index('election_id')

    elector_contract = lite_client.get_config(1)['elector_addr']
    if elector_contract[0] == 'x':
        elector_contract = f'-1:{elector_contract[1:]}'

    election_id = lite_client.run_method(elector_contract, 'active_election_id')[0]

    if election_id == 0:
        # Run `participant_list_extended` at the moment before closing election.
        # Note: election_id is end timestamp of next validation cycle.
        election_is_in_progress = False
        last_election_ids = lite_client.run_method(elector_contract, 'past_election_ids')[0]
        election_id = max([int(id) for id in last_election_ids])

        prev_saved_election = elections_collection.find_one({
            'election_id': {
                '$eq' : election_id
            }
        })
        if prev_saved_election is not None and prev_saved_election['finished']:
            return 'This elections is finished and already exists in DB'
        
        config15 = lite_client.get_config(15)
        elections_end_before = config15['elections_end_before']
        ELECTION_CLOSE_THRESHOLD = 10
        before_closing_election = election_id - elections_end_before - ELECTION_CLOSE_THRESHOLD

        participants_info = lite_client.run_method_full(elector_contract, 'participant_list_extended', timestamp=before_closing_election)
    else:
        # Calling run_method_full with timestamp set as now() with small offset as workaround for bug: 
        # run_method returnes parsing error in lite-client.
        election_is_in_progress = True
        NOW_THRESHOLD = 10
        now_timestamp = int(datetime.utcnow().timestamp() - NOW_THRESHOLD)
        participants_info = lite_client.run_method_full(elector_contract, 'participant_list_extended', timestamp=now_timestamp)

    elect_at = int(participants_info[0])
    elect_close = int(participants_info[1])
    min_stake = int(participants_info[2])
    total_stake = int(participants_info[3])
    participant_list_raw = participants_info[4]
    # failed = bool(participants_info[5])
    # finished = bool(participants_info[6])

    if elect_at != election_id:
        raise Exception(f'Inconsistency error: election_id={election_id}, elect_at={elect_at}')

    participant_list = []
    for participant_raw in participant_list_raw:
        wallet_address = participant_raw[1][2]
        wallet_address = "-1:" + Dec2HexAddr(wallet_address)
        wallet_address = HexAddr2Base64Addr(wallet_address)
        participant_list.append({
            'pubkey': Dec2HexAddr(participant_raw[0]),
            'stake': participant_raw[1][0],
            'max_factor': participant_raw[1][1],
            'wallet_address': wallet_address,
            'adnl_addr': Dec2HexAddr(participant_raw[1][3])
        })


    election_data = {
        'election_id': election_id,
        'elect_close': elect_close,
        'min_stake': min_stake,
        'total_stake': total_stake,
        'participants_list': participant_list,
        'finished': not election_is_in_progress
    }

    elections_collection.replace_one({'election_id' : {'$eq': election_id}}, election_data, upsert=True)

    return f"Election {election_id} was added/updated"

@app.task(autoretry_for=(LiteClientException,), default_retry_delay=1, max_retries=5)
def update_complaints():
    with open(constants.MONGO_PASSWORD_FILE, 'r') as f:
        password = f.read()
    client = MongoClient(host=constants.MONGO_HOST, 
                         port=constants.MONGO_PORT,
                         username=constants.MONGO_USER,
                         password=password)
    complaints_collection = client[constants.MONGO_DATABASE]['complaints_data']
    complaints_collection.create_index('election_id')
    elections_collection = client[constants.MONGO_DATABASE]['elections_data']

    elector_contract = lite_client.get_config(1)['elector_addr']
    if elector_contract[0] == 'x':
        elector_contract = f'-1:{elector_contract[1:]}'

    complaints = []
    for val_cycle in [32, 34]:
        cycle_complaints = lite_client.get_complaints_list(val_cycle)

        # Set wallet_address for each complaint. TODO: Refactor it.
        if len(cycle_complaints) == 0:
            continue
        election_req = elections_collection.find_one({'election_id': {'$eq' : cycle_complaints[0]['election_id']}})
        if election_req:
            for complaint in cycle_complaints:
                try:
                    participant = next(participant for participant in election_req['participants_list'] if participant['pubkey'] == complaint['pubkey'])
                    wallet_address = participant['wallet_address']
                except StopIteration:
                    wallet_address = None
                complaint['wallet_address'] = wallet_address
                
        complaints += cycle_complaints
    
    for complaint in complaints:
        complaints_collection.replace_one({'pseudohash' : {'$eq': complaint['pseudohash']}}, complaint, upsert=True)
