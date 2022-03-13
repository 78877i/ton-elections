import subprocess
from typing import Optional
from indexer.utils import Tlb2Json, Result2List, Pars, Dec2HexAddr, HexAddr2Base64Addr

class LiteClientException(Exception):
    pass

class LiteClient:
    def __init__(self, binary_path: str, config_path: str):
        self.binary_path = binary_path
        self.config_path = config_path

    def _run(self, cmd, **kwargs):
        timeout = kwargs.get("timeout", 10)
        index = kwargs.get("index")
        args = [self.binary_path, "--global-config", self.config_path, "--verbosity", "0", "--cmd", cmd]
        if index is not None:
            index = str(index)
            args += ["-i", index]

        try:
            process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise LiteClientException(f"LiteClient timeout. Output: \n {e.output}")

        output = process.stdout.decode("utf-8")
        err = process.stderr.decode("utf-8")
        if len(err) > 0:
            raise LiteClientException("LiteClient error: {err}".format(err=err))
        return output

    def get_config(self, config_id: int):
        cmd = f'getconfig {config_id}'
        result = self._run(cmd)
        start = result.find("ConfigParam")
        text = result[start:]
        return Tlb2Json(text)

    def run_method(self, addr: str, method: str, params: list = []):
        result = self._run(f"runmethod {addr} {method} {' '.join(params)}")
        return Result2List(result)

    def run_method_full(self, addr: str, method: str, params: list = [], timestamp: Optional[int] = None):
        params = list(map(str, params))
        if timestamp is not None:
            block_id_ext_raw = self._run(f'byutime -1:8000000000000000 {timestamp}')
            block_id_ext = Pars(block_id_ext_raw, 'reference masterchain block : ', '\n')
            if block_id_ext is None:
                raise Exception('Block not found by unixtime.')
            result = self._run(f"runmethodfull {addr} {block_id_ext} {method} {' '.join(params)}")
        else:
            result = self._run(f"runmethodfull {addr} {method} {' '.join(params)}")
        return Result2List(result)

    def get_config_17(self):
        config = self.get_config(17)
        config17 = dict()
        config17["min_stake"] = config["min_stake"]["amount"]["value"]
        config17["max_stake"] = config["max_stake"]["amount"]["value"]
        config17["max_stake_factor"] = config["max_stake_factor"]
        return config17

    def get_validators_list(self, config_id: int):
        if config_id not in [32, 34, 36]:
            raise ValueError("config_id has to be 32, 34, 36")

        config = dict()
        result = self._run(f'getconfig {config_id}')
        if '= (null)' in result:
            return None
        config["total"] = int(Pars(result, "total:", ' '))
        config["utime_since"] = int(Pars(result, "utime_since:", ' '))
        config["utime_until"] = int(Pars(result, "utime_until:", ' '))
        config["total_weight"] = int(Pars(result, "total_weight:", ' '))
        lines = result.split('\n')
        validators = list()
        for line in lines:
            if "public_key:" in line:
                validatorAdnlAddr = Pars(line, "adnl_addr:x", ')')
                pubkey = Pars(line, "pubkey:x", ')')
                validatorWeight = int(Pars(line, "weight:", ' '))
                buff = dict()
                buff["adnl_addr"] = validatorAdnlAddr
                buff["pubkey"] = pubkey
                buff["weight"] = validatorWeight
                buff["index"] = len(validators)
                validators.append(buff)
        config["validators"] = validators
        return config

    def get_complaints_list(self, config_id: int):
        if config_id not in [32, 34]:
            raise ValueError("config_id has to be 32, 34")

        elector_contract = self.get_config(1)['elector_addr']
        if elector_contract[0] == 'x':
            elector_contract = f'-1:{elector_contract[1:]}'

        val_config = self.get_validators_list(config_id)
        election_id = val_config['utime_since']
        complaints_raw = self.run_method_full(elector_contract, 'list_complaints', [election_id])

        if complaints_raw is None:
            return []

        complaints_raw = complaints_raw[0]

        complaints = []
        total_weight = val_config["total_weight"]
        for complaint in complaints_raw:
            if len(complaint) == 0:
                continue
            chash = complaint[0]
            subdata = complaint[1]

            # Create dict
            # parser from: https://github.com/ton-blockchain/ton/blob/dab7ee3f9794db5a6d32c895dbc2564f681d9126/crypto/smartcont/elector-code.fc#L1149
            item = dict()
            buff = subdata[0] # *complaint*
            item["election_id"] = election_id
            item["hash"] = str(chash)
            pubkey = Dec2HexAddr(buff[0]) # *validator_pubkey*
            adnl = next(val['adnl_addr'] for val in val_config['validators'] if val['pubkey'] == pubkey)
            item["pubkey"] = pubkey
            item["adnl_addr"] = adnl
            item["description"] = buff[1] # *description*
            item["created_time"] = buff[2] # *created_at*
            item["severity"] = buff[3] # *severity*
            reward_addr = buff[4]
            reward_addr = "-1:" + Dec2HexAddr(reward_addr)
            reward_addr = HexAddr2Base64Addr(reward_addr)
            item["reward_addr"] = reward_addr # *reward_addr*
            item["paid"] = buff[5] # *paid*
            item["suggested_fine"] = buff[6] # *suggested_fine*
            item["suggested_fine_part"] = buff[7] # *suggested_fine_part*
            voted_validators = subdata[1] # *voters_list*
            item["voted_validators"] = voted_validators
            item["vset_id"] = str(subdata[2]) # *vset_id*
            weight_remaining = subdata[3] # *weight_remaining*
            required_weight = total_weight * 2 / 3
            if len(voted_validators) == 0:
                weight_remaining = required_weight
            available_weight = required_weight - weight_remaining
            item["weight_remaining"] = weight_remaining
            item["approved_percent"] = round(available_weight / total_weight * 100, 3)
            item["is_passed"] = (weight_remaining < 0)
            pseudohash = pubkey + str(election_id)
            item["pseudohash"] = pseudohash
            complaints.append(item)

        return complaints
