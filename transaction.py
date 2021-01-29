#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

import logging
import requests

import subprocess
from shlex import split
import re
from datetime import datetime

from chainlibpy import Transaction, Wallet

class Envoi ():
    def __init__(self, wallet, account_num):
        self.wallet_1 = wallet
        self.address_1 = self.wallet_1.address
        print(self.address_1)
        self.account_num = account_num
        self.mode = "sync"

    def get_address(self):
        return self.address_1

    def set_mode(self, mode):
        self.mode = mode

    def get_pushTx(self, amount, sequence):
        tx = Transaction(
            wallet=self.wallet_1,
            account_num=self.account_num,
            sequence=sequence,
            chain_id="crossfire",
            fee=20000,
            fee_denom="basetcro",
            gas=200000,
            sync_mode=self.mode
        )
        tx.add_transfer(to_address=self.address_1, amount=amount, base_denom="basetcro")
        signed_tx = tx.get_pushable()
        return signed_tx


# wait for the next block height
# can be usefull to restart the service between 2 block and
# limite the lost of commits
def sync_block(request_session):
    url_info = "http://localhost:26657/status"
    start_block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"]) 
    while True:
        block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"])
        print(f"wait new block {block} {start_block}", end='\r')
        if block == start_block:
            time.sleep(1)
            continue
        else:
            print("")
            break
    time.sleep(0.1)

def main():
    print("### STARTING FLODDING ###")
    
    # create a wallet from my seed
    seed = "warrior sponsor tiger lift ship clog shrimp rent critic pony isolate clever lake notable gas enlist photo whisper excite toy master future van universe"
    wallet_1 = Wallet(seed)
    address_1 = wallet_1.address
    print(address_1)
    
    # define my delegator address
    delegatorAddr = "crocncl13njqv0la9cw2mr80utsmeppmtxk57kfggpnhly"
    
    # define all the endpoint we can need
    
    # the api port setted in ${home_dir of chain-maind}/config/app.toml, the default is ~/.chain-maind/config/app.toml
    crypto_url = "https://crossfire-lcd.crypto.com/"
    local_url = "http://localhost:1317"
    health = "http://localhost:26657/health"
    url_tx = f"{local_url}/txs"
    #url_info = f"https://crossfire.crypto.com:443/status"
    url_info = f"http://localhost:26657/status"
    url_account = f"{local_url}/cosmos/auth/v1beta1/accounts/{address_1}"
    url_balance = f"{local_url}/cosmos/bank/v1beta1/balances/{address_1}"
    url_withdraw = f"{local_url}/distribution/delegators/{delegatorAddr}/rewards"

    # init request session to reuse tcp socket
    r = requests.Session()
    response = r.get(url_account)
    account_info = response.json()["account"]
    account_num = int(account_info["account_number"])
    sequence = int(account_info["sequence"])
    
    # create transaction object
    send_object = Envoi(wallet_1, account_num)
    
    #create a logger
    logger = logging.getLogger('mylogger')

    seq = 0

    now = datetime.now()
    amount = 1 * 10 ** 8
    # get the account info
    while True:
        # get the balance of address_1
        response = r.get(url_balance)
        balance_1 = int(response.json()["balances"][0]["amount"])
        
        if account_num == 0 or sequence == 0:
            # get account number and sequence ID
            response = r.get(url_account)
            account_info = response.json()["account"]
            account_num = int(account_info["account_number"])
            sequence = int(account_info["sequence"])
            print(f"account number {account_num}")
            print(f"retrieve sequence num : {sequence}")
        
        print(f"balance of address 1: {balance_1}")

        # check the balance is enought to not drain all our tcro
        if balance_1 >= 4000000 :
            # define last sequence number for the loop
            stop_at = sequence + 500
            seq = sequence
            for seq in range(sequence, stop_at):
            #while True:
                # make transaction
                signed_tx = send_object.get_pushTx(amount=1, sequence=seq)
                try:
                    # send the Tx
                    response = r.post(url_tx, json=signed_tx)
                    response.raise_for_status()
                except http_error as e:
                    print(e)
                    time.sleep(1)
                    continue

                result = response.json()
                code = result.get("code")
                # error code managment
                if not code:
                    print(response.text)
                    # update sequence start number
                    seq += 1
                    sequence = seq
                    continue
                if code == 0:
                    print(f"error {code} tx OK")
                    # increment the sequence number
                    seq += 1
                    # update sequence start number
                    sequence = seq
                    send_object.set_mode("async")
                elif  code == 4:
                    print(f"sequence {seq} error {code} unauthorized")
                    # unauthorized
                    print(response.text)
                    p = re.compile('\d+')
                    int(p.findall(result['raw_log'])[1])
                    # update sequence start number
                    seq = 0
                    sequence = seq
                    break
                elif  code == 19:
                    # the Tx already exist, sequence number not up to date
                    print(f"error {code} tx {seq} already in mempool", end='\n')
                    # force retrieve sequence num
                    seq = 0
                    # update sequence start number
                    sequence = seq
                    break
                elif  code == 20:
                    # mempool is full, give time to purge
                    print(f"index {seq} error {code} mempool is full")
                    # update sequence start number
                    sequence = seq
                    break
                elif  code == 32:
                    print(f"index {seq} error {code} sequence error (congestion?)")
                else :
                    # any other code
                    print(f"index {seq} error {code} ")
                    seq = 0
            # update sequence start number
            sequence = seq
            # end for loop
            sync_block(r)
            #time.sleep(5)
        else:
            print("no Tcro left")
            withdraw_cmd = f"chain-maind tx distribution withdraw-all-rewards --from {address_1} -y --gas-prices 0.1basetcro --chain-id crossfire --keyring-backend test --home /home/dpierret/.chain-maind"
            subprocess.run(split(withdraw_cmd))

if __name__ == "__main__":
    main()
