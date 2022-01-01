#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

import logging
import requests

import subprocess
import re
from datetime import datetime

from requests.models import HTTPError

from chainlibpy import Transaction, Wallet


class Envoi():
    def __init__(self, wallet, account_num: int, chain_id: str, denom: str):
        self.wallet_1 = wallet
        self.address_1 = self.wallet_1.address
        self.account_num = account_num
        self.mode = "sync"
        self.chain_id = chain_id
        self.denom = denom

    def get_address(self):
        return self.address_1

    def set_mode(self, mode):
        self.mode = mode

    def get_pushTx_sync(self, amount, to, sequence, timeout_block):
        tx = Transaction(
            wallet=self.wallet_1,
            account_num=self.account_num,
            sequence=sequence,
            chain_id=self.chain_id,
            fee=20000,
            fee_denom=self.denom,
            gas=200000,
            sync_mode=self.mode,
            memo=str(datetime.now()),
            timeout=timeout_block,
        )
        tx.add_transfer(to_address=to, amount=amount, base_denom=self.denom)
        signed_tx = tx.get_pushable()
        return signed_tx


# wait for the next block height
# can be usefull to restart the service between 2 block and
# limite the lost of commits
def sync_block(request_session):
    url_info = "http://127.0.0.1:26657/status"
    start_block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"])
    while True:
        block = int(request_session.get(url_info).json()["result"]["sync_info"]["latest_block_height"])
        # print(f"wait new block {block} {start_block}", end='\r')
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
    seed = input("enter the seed of the sender wallet :")
    # seed = "slogan initial run clock nasty clever aisle trumpet label doll comic fit gas game casino knife outside hunt genuine nerve mad notable alarm camera"

    # wallet_1 = Wallet(seed, path="m/44'/1'/0'/0/0", hrp="tcro")
    path = "m/44'/118'/0'"
    hrp = "juno"
    wallet_1 = Wallet(seed, path, hrp)
    address_1 = wallet_1.address
    print(address_1)
    if input("is this address correct ? [Y/n]:") == 'n':
        exit(1)

    address_2 = input("enter the receiver address")
    send_amount = int(input("enter the amount to save expressed in ujuno"))

    # the api port setted in ${home_dir of chain-maind}/config/app.toml, the default is ~/.chain-maind/config/app.toml
    local_url = "https://lcd.juno.disperze.network"
    url_tx = f"{local_url}/txs"
    url_block = f"https://rpc.juno.disperze.network/block"
    url_account = f"{local_url}/cosmos/auth/v1beta1/accounts/{address_1}"
    url_balance = f"{local_url}/cosmos/bank/v1beta1/balances/{address_1}"

    # init request session to reuse tcp socket
    r = requests.Session()
    response = r.get(url_account)
    account_info = response.json()["account"]
    account_num = int(account_info["account_number"])
    sequence = int(account_info["sequence"])
    stop_at = sequence

    # create transaction object
    send_object = Envoi(wallet_1, account_num, chain_id="juno-1", denom="ujuno")
    send_object.set_mode("sync")

    # create a logger
    logger = logging.getLogger('mylogger')

    seq = 0

    now = datetime.now()
    break_block = 0
    # get the account info
    while True:
        # get the balance of address_1
        response = r.get(url_balance)
        balance_1 = int(response.json()["balances"][0]["amount"])

        # if account_num == 0 or sequence == 0:
        # get account number and sequence ID
        response = r.get(url_account)
        account_info = response.json()["account"]
        account_num = int(account_info["account_number"])
        sequence = int(account_info["sequence"])
        response = r.get(url_block)
        block_height = int(response.json()["result"]["block"]["header"]["height"])
        if (sequence != stop_at) and (break_block >= block_height):
            print(f"{block_height} {sequence} different than {stop_at}", end='\r')
            sync_block(r)
            # time.sleep(1)
            continue
        else:
            print("")
        send_object.set_mode("sync")

        print(f"balance of address 1: {balance_1}")
        print(f"sequence start: {sequence}")

        # define last sequence number for the loop
        stop_at = sequence + 100
        seq = sequence
        for seq in range(sequence, stop_at):
            # while True:
            # make transaction
            break_block = block_height + 20
            signed_tx = send_object.get_pushTx_sync(amount=1, to=address_2, sequence=seq, timeout_block=break_block)
            try:
                # send the Tx
                response = r.post(url_tx, json=signed_tx)
                response.raise_for_status()
            except HTTPError as e:
                time.sleep(0.1)
                continue

            result = response.json()
            code = result.get("code")
            # error code managment
            if not code:
                print(block_height + 5, end=' ')
                print(seq, end=' ')
                # print(response.text)
                print(response.text)
                # update sequence start number
                seq += 1
                sequence = seq
                # send_object.set_mode("async")
                continue
            if code == 0:
                print(f"error {code} tx OK")
                # increment the sequence number
                seq += 1
                # update sequence start number
                sequence = seq
            elif code == 4:
                print(f"sequence {seq} error {code} unauthorized")
                # unauthorized
                print(response.text)
                p = re.compile('\d+')
                int(p.findall(result['raw_log'])[1])
                time.sleep(5)
                # force retrieve sequence num
                seq = 0
                sequence = seq
                exit("resync")
                break
            elif code == 19:
                # the Tx already exist, sequence number not up to date
                print(f"error {code} tx {seq} already in mempool", end='\n')
                # force retrieve sequence num
                seq = 0
                # update sequence start number
                sequence = seq
                break
            elif code == 20:
                # mempool is full, give time to purge
                print(f"index {seq} error {code} mempool is full")
                # update sequence start number
                sequence = seq
                stop_at = seq
                break

            elif code == 32:
                print(f"index {seq} error {code} sequence error (congestion?)")
            else:
                # any other code
                print(f"index {seq} error {code} ")
                seq = 0
                exit("new unknow error")
            # update sequence start number
            sequence = seq
            # end for loop
            # sync_block(r)
            # send_object.set_mode("sync")
            time.sleep(2)


if __name__ == "__main__":
    main()
