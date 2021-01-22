#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import requests

from chainlibpy import Transaction, Wallet

def send_tx(seq: int, mode: str):
    # make transaction
    tx = Transaction(
        wallet=wallet_1,
        account_num=account_num,
        sequence=seq,
        chain_id="crossfire",
        fee=20000,
        fee_denom="basetcro",
        gas=200000,
        sync_mode=mode
    )
    seq += 1
    tx.add_transfer(to_address=address_1, amount=amount)

    signed_tx = tx.get_pushable()
    response = requests.post(url_tx, json=signed_tx)
    if not response.ok:
        raise Exception(response.reason)
    result = response.json()
    code = result.get("code")
    if code :
        print(f"error : {code}")
        print(result)
        raise Exception(result["raw_log"])

def main():
    print("### STARTING FLODDING ###")
    seed = "warrior sponsor tiger lift ship clog shrimp rent critic pony isolate clever lake notable gas enlist photo whisper excite toy master future van universe"
    wallet_1 = Wallet(seed)
    address_1 = wallet_1.address
    print(address_1)
    delegatorAddr = "crocncl13njqv0la9cw2mr80utsmeppmtxk57kfggpnhly"

    # the api port setted in ${home_dir of chain-maind}/config/app.toml, the default is ~/.chain-maind/config/app.toml
    crypto_url = "https://crossfire-lcd.crypto.com/"
    local_url = "http://localhost:1317"
    url_tx = f"{local_url}/txs"
    url_account = f"{crypto_url}/cosmos/auth/v1beta1/accounts/{address_1}"
    url_balance = f"{crypto_url}/cosmos/bank/v1beta1/balances/{address_1}"
    url_withdraw = f"{local_url}/distribution/delegators/{delegatorAddr}/rewards"

    r = requests.Session()
    sequence = 0;
    # get the account info
    while True:
        # get the balance of address_1
        response = r.get(url_balance)
        balance_1 = int(response.json()["balances"][0]["amount"])
        response = r.get(url_account)
        account_info = response.json()["account"]
        account_num = int(account_info["account_number"])
        if int(account_info["sequence"]) == sequence :
            print(".", end = '')
            time.sleep(1)
            continue
        else :
            print(f"balance of address 1: {balance_1}")
        sequence = int(account_info["sequence"])
        stop_at = sequence + 150;
        amount = 1 * 10 ** 8
        if balance_1 >= 4000000 :
            seq = 0
            print(f"send sequence {sequence} to {stop_at}")
            for seq in range(sequence, stop_at):
                # make transaction
                tx = Transaction(
                    wallet=wallet_1,
                    account_num=account_num,
                    sequence=seq,
                    chain_id="crossfire",
                    fee=20000,
                    fee_denom="basetcro",
                    gas=200000,
                    sync_mode="sync"
                )
                seq += 1
                tx.add_transfer(to_address=address_1, amount=amount)

                signed_tx = tx.get_pushable()
                try:
                    response = r.post(url_tx, json=signed_tx)
                    if not response.ok:
                        time.sleep(1)
                        raise Exception(response.reason)
                    result = response.json()
                    code = result.get("code")
                    if code :
                        print(code)
                        time.sleep(1)
                        raise Exception(result['raw_log'])
                except Exception as identifier:
                    break
            # end for loop
            """ print(f"send sequence block: {seq}")
            # make transaction
            tx = Transaction(
                wallet=wallet_1,
                account_num=account_num,
                sequence=stop_at,
                chain_id="crossfire",
                fee=20000,
                fee_denom="basetcro",
                gas=200000,
                sync_mode="sync"
            )
            seq += 1
            tx.add_transfer(to_address=address_1, amount=amount)

            signed_tx = tx.get_pushable()
            try:
                response = r.post(url_tx, json=signed_tx)
                if not response.ok:
                    print(response.reason)
                    time.sleep(1)
                    #raise Exception(response.reason)
                else:
                    result = response.json()
                    code = result.get("code")
                    if code :
                        print(f"error : {code}")
                        print(result)
                        raise Exception(result['raw_log'])
            except: 
                pass """
        else:
            print("no Tcro left")
            #data= {"base_req":{"from": "{}", \"memo\": \"Sent via Cosmos Voyager 🚀\", \"chain_id\": \"Cosmos-Hub\", \"account_number\": \"0\", \"sequence\": \"1\", \"gas\": \"200000\", \"gas_adjustment\": \"1.2\", \"fees\": [ { \"denom\": \"stake\", \"amount\": \"50\" } ], \"simulate\": false }}
            #response = requests.post(url_withdraw)

if __name__ == "__main__":
    main()

