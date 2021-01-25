#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from dbus import SystemBus, Interface
from dbus.exceptions import DBusException
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

    def get_address(self):
        return self.address_1

    def get_pushTx_sync(self, amount, sequence):
        tx = Transaction(
            wallet=self.wallet_1,
            account_num=self.account_num,
            sequence=sequence,
            chain_id="crossfire",
            fee=20000,
            fee_denom="basetcro",
            gas=200000,
            sync_mode="sync"
        )
        tx.add_transfer(to_address=self.address_1, amount=amount)
        signed_tx = tx.get_pushable()
        return signed_tx

def is_service_running(service):
    """ Queries systemd through dbus to see if the service is running """
    service_running = False
    bus = SystemBus()
    systemd = bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')
    try:
        service_unit = service if service.endswith('.service') else manager.GetUnit('{0}.service'.format(service))
        service_proxy = bus.get_object('org.freedesktop.systemd1', str(service_unit))
        service_properties = Interface(service_proxy, dbus_interface='org.freedesktop.DBus.Properties')
        service_load_state = service_properties.Get('org.freedesktop.systemd1.Unit', 'LoadState')
        service_active_state = service_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')
        if service_load_state == 'loaded' and service_active_state == 'active':
            service_running = True
    except DBusException:
        pass

    return service_running

def is_service_active(service):
    """
    is_service_active method will check if service is running or not.
    It raise exception if there is service is not loaded
    Return value, True if service is running otherwise False.
    :param str service: name of the service
    """

    bus = SystemBus()
    systemd = bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd, 'org.freedesktop.systemd1.Manager')

    try:
        manager.GetUnit('chain-maind.service')
        return True
    except:
        return False

def restart_daemon():
    cmd = f"systemctl restart chain-maind"
    print("### Restart service ###")
    sysbus = SystemBus()
    systemd1 = sysbus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd1, dbus_interface='org.freedesktop.systemd1.Manager')
    if is_service_active('chain-maind.service'):
        manager.StopUnit('chain-maind.service', 'replace')
     #job = manager.RestartUnit('chain-maind.service', 'fail')
    time.sleep(10)
    manager.StartUnit('chain-maind.service', 'replace')
    exit("Chain-maind restart")

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
    health = "http://localhost:26657/health"
    url_tx = f"{local_url}/txs"
    #url_info = f"https://crossfire.crypto.com:443/status"
    url_info = f"http://localhost:26657/status"
    url_account = f"{local_url}/cosmos/auth/v1beta1/accounts/{address_1}"
    url_balance = f"{local_url}/cosmos/bank/v1beta1/balances/{address_1}"
    url_withdraw = f"{local_url}/distribution/delegators/{delegatorAddr}/rewards"


    r = requests.Session()
    response = r.get(url_account)
    account_info = response.json()["account"]
    account_num = int(account_info["account_number"])
    sequence = int(account_info["sequence"])

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
        response = r.get(url_account)
        account_info = response.json()["account"]
        account_num = int(account_info["account_number"])
        sequence = int(account_info["sequence"])

        print(f"retrieve sequence num : {sequence}")
        print(f"balance of address 1: {balance_1}")

        if balance_1 >= 4000000 :
            stop_at = sequence + 200
            for seq in range(sequence, stop_at):
            #while True:
                # make transaction
                signed_tx = send_object.get_pushTx_sync(amount=1, sequence=seq)
                try:
                    response = r.post(url_tx, json=signed_tx)
                    response.raise_for_status()
                except http_error as e:
                    print(e)
                    time.sleep(1)
                    continue

                result = response.json()
                code = result.get("code")
                if not code:
                    print(response.text)
                    continue
                if code == 0:
                    print(f"error {code} tx OK")
                    seq = seq + 1
                elif  code == 4:
                    print(f"sequence {seq} error {code} unauthorized")
                    # unauthorized
                    p = re.compile('\d+')
                    int(p.findall(result['raw_log'])[1])
                elif  code == 19:
                    print(f"error {code} tx already in mempool", end='\r')
                    continue
                elif  code == 20:
                    print(f"index {seq} error {code} mempool is full")
                    time.sleep(1)
                    break
                elif  code == 32:
                    print(f"index {seq} error {code} sequence error (congestion)")
                else :
                    print(f"index {seq} error {code} ")
            time.sleep(1)
            # end for loop
        else:
            print("no Tcro left")
            withdraw_cmd = f"chain-maind tx distribution withdraw-all-rewards --from {address_1} -y --gas-prices 0.1basetcro --chain-id crossfire --keyring-backend test --home /home/dpierret/.chain-maind"
            subprocess.run(split(withdraw_cmd))

if __name__ == "__main__":
    main()
