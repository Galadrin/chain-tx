#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import multiprocessing
import os
import random
import re
import time

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import subprocess
from datetime import datetime

from cosmpy.aerial.client import LedgerClient, create_bank_send_msg, prepare_and_broadcast_basic_transaction
from cosmpy.aerial.config import NetworkConfig
from cosmpy.aerial.exceptions import OutOfGasError, BroadcastError
from cosmpy.aerial.tx import Transaction, SigningCfg
from cosmpy.aerial.tx_helpers import SubmittedTx
from cosmpy.crypto.address import Address
from cosmpy.crypto.keypairs import PrivateKey
from cosmpy.protos.cosmos.tx.v1beta1.service_pb2 import BroadcastMode, BroadcastTxRequest

from cosmpy.aerial.wallet import LocalWallet, Wallet

RPC_LIST = ['https://okp4-rpc.42cabi.net:443', 'https://rpc.okp4.indonode.net:443',
            'https://okp4-rpc.punq.info:443',
            ]
REST_LIST = ['rest+https://okp4-api.42cabi.net', 'rest+https://api.okp4.indonode.net/',
             'rest+https://api.okp.ppnv.space'
             ]

class MyLedgerClient(LedgerClient):
    def broadcast_tx(self, tx: Transaction, sync: bool = False):
        """Broadcast transaction.

        :param tx: transaction
        :param sync: sync or async transaction
        :return: Submitted transaction
        """
        # create the broadcast request
        broadcast_req = BroadcastTxRequest(
            tx_bytes=tx.tx.SerializeToString(),
            mode=BroadcastMode.BROADCAST_MODE_SYNC if sync else BroadcastMode.BROADCAST_MODE_ASYNC
        )

        # broadcast the transaction
        resp = self.txs.BroadcastTx(broadcast_req)
        if sync:
            tx_digest = resp.tx_response.txhash

            # check that the response is successful
            initial_tx_response = self._parse_tx_response(resp.tx_response)
            initial_tx_response.ensure_successful()

            return SubmittedTx(self, tx_digest)

    def prepare_send_tokens(
            self,
            destination: Address,
            amount: int,
            denom: str,
            sender: Wallet,
            account: Optional["Account"] = None,  # type: ignore # noqa: F821
            memo: Optional[str] = None,
            gas_limit: Optional[int] = None
    ):
        """Send tokens.

        :param destination: destination address
        :param amount: amount
        :param denom: denom
        :param sender: sender
        :param memo: memo, defaults to None
        :param gas_limit: gas limit, defaults to None
        :return: prepare and broadcast the transaction and transaction details
        """
        # build up the store transaction
        tx = Transaction()
        tx.add_message(
            create_bank_send_msg(sender.address(), destination, amount, denom)
        )

        return prepare_basic_transaction(
            self, tx, sender, gas_limit=gas_limit, memo=memo, account=account
        )

    def send_tokens(
            self,
            destination: Address,
            amount: int,
            denom: str,
            sender: Wallet,
            account: Optional["Account"] = None,  # type: ignore # noqa: F821
            memo: Optional[str] = None,
            gas_limit: Optional[int] = None
    ) -> SubmittedTx:
        """Send tokens.

        :param destination: destination address
        :param amount: amount
        :param denom: denom
        :param sender: sender
        :param memo: memo, defaults to None
        :param gas_limit: gas limit, defaults to None
        :return: prepare and broadcast the transaction and transaction details
        """
        # build up the store transaction
        tx = Transaction()
        tx.add_message(
            create_bank_send_msg(sender.address(), destination, amount, denom)
        )

        return prepare_and_broadcast_basic_transaction(
            self, tx, sender, gas_limit=gas_limit, memo=memo, account=account
        )


netconf = NetworkConfig(chain_id="okp4-nemeton-1",
                        fee_minimum_gas_price=0.0025,
                        fee_denomination='uknow',
                        staking_denomination='uknow',
                        url='rest+https://okp4-api.42cabi.net/'
                        )
ledger = MyLedgerClient(netconf)


def broadcast_basic_transaction(
        client: "LedgerClient",  # type: ignore # noqa: F821
        tx: "Transaction",  # type: ignore # noqa: F821
) -> SubmittedTx:
    return client.broadcast_tx(tx)


def prepare_basic_transaction(
        client: "LedgerClient",  # type: ignore # noqa: F821
        tx: "Transaction",  # type: ignore # noqa: F821
        sender: "Wallet",  # type: ignore # noqa: F821
        account: Optional["Account"] = None,  # type: ignore # noqa: F821
        gas_limit: Optional[int] = None,
        memo: Optional[str] = None,
) -> Transaction:
    """Prepare basic transaction.

    :param client: Ledger client
    :param tx: The transaction
    :param sender: The transaction sender
    :param account: The account
    :param gas_limit: The gas limit
    :param memo: Transaction memo, defaults to None

    :return: broadcast transaction
    """
    # query the account information for the sender
    if account is None:
        account = client.query_account(sender.address())

    if gas_limit is not None:
        # simply build the fee from the provided gas limit
        fee = client.estimate_fee_from_gas(gas_limit)
    else:

        # we need to build up a representative transaction so that we can accurately simulate it
        tx.seal(
            SigningCfg.direct(sender.public_key(), account.sequence),
            fee="",
            gas_limit=0,
            memo=memo,
        )
        tx.sign(sender.signer(), client.network_config.chain_id, account.number)
        tx.complete()

        # simulate the gas and fee for the transaction
        gas_limit, fee = client.estimate_gas_and_fee_for_tx(tx)

    # finally, build the final transaction that will be executed with the correct gas and fee values
    tx.seal(
        SigningCfg.direct(sender.public_key(), account.sequence),
        fee=fee,
        gas_limit=gas_limit,
        memo=memo,
    )
    tx.sign(sender.signer(), client.network_config.chain_id, account.number)
    tx.complete()

    return tx


def spam(wallet: LocalWallet):
    gas = 70000
    sequence = 0
    check_tx = True
    print(f"start thread for wallet: {wallet.address()}")
    netconf = NetworkConfig(chain_id="okp4-nemeton-1",
                            fee_minimum_gas_price=0.0025,
                            fee_denomination='uknow',
                            staking_denomination='uknow',
                            url=REST_LIST[random.randint(0, len(REST_LIST)-1)]
                            )
    ledger = MyLedgerClient(netconf)

    try:
        # get the account info
        account = ledger.query_account(wallet.address())
        address = wallet.address()
        sequence = account.sequence
        balance = ledger.query_bank_balance(wallet.address())
        print(f"account {address}: balance {balance}")
    except Exception as err:
        print(err)
    while True:
        # get the balance of address_1
        print(f"sequence start: {sequence}")
        # define last sequence number for the loop
        stop_at = sequence + 100000
        seq = sequence

        for seq in range(sequence, stop_at):
            try:
                if check_tx:
                    tx = ledger.prepare_send_tokens(destination=address,
                                                    amount=1,
                                                    denom="uknow",
                                                    sender=wallet,
                                                    account=account,
                                                    memo="stress test",
                                                    gas_limit=gas
                                                    )
                    sent_tx = ledger.broadcast_tx(tx, True)
                    #check_tx = False
                else:
                    sent_tx = ledger.send_tokens(destination=address,
                                                 amount=1,
                                                 denom="uknow",
                                                 sender=wallet,
                                                 account=account,
                                                 memo="stress test",
                                                 gas_limit=gas
                                                 )
            except OutOfGasError as err:
                gas += err.gas_wanted
                print(f"increase gas to {gas}")
            except BroadcastError as err:
                """
                tx = ledger.wait_for_query_tx(tx_hash=err.tx_hash)
                # mempool full
                if tx.code == 20:
                    print(f"mempool is full at Tx: {err.tx_hash}")
                    time.sleep(10)
                # sequence missmatch
                elif tx.code == 32:
                    
                else:
                """
                if "account sequence mismatch" in str(err):
                    match = re.search(r"expected \s*(\d+\w+)", str(err))
                    if match is not None:
                        required_sequence = match.group(1)
                        account.sequence = int(required_sequence)
                        print(f"wallet {address} reset sequence to {account.sequence}")
                    else:
                        print("cannot match")
                else:
                    print(f"wallet {address} error {err} (waiting)")
                    time.sleep(30)
            except Exception as err:
                print(f"wallet {address} error {err}")
            else:
                account.sequence += 1


def main():
    print("### STARTING FLODDING ###")

    # create a wallet from my seed
    SEED = "slogan initial run clock nasty clever aisle trumpet label doll comic fit gas game casino knife outside hunt genuine nerve mad notable alarm camera"
    CPU_NUM = multiprocessing.cpu_count()

    spam_wallet = LocalWallet.from_mnemonic(mnemonic=SEED, prefix="okp4")
    spam_account = ledger.query_account(spam_wallet.address())
    slave_wallets = []

    print(f"create {CPU_NUM} wallets")
    if os.path.exists(os.path.join(os.getenv('HOME'), '.okp4', 'spam_wallets.json')):
        j = json.load(open(os.path.join(os.getenv('HOME'), '.okp4', 'spam_wallets.json'), 'r'))
        for wallet in j:
            slave_wallets.append(LocalWallet(private_key=PrivateKey(wallet['private_key']), prefix='okp4'))
    else:
        for cpu in range(0, CPU_NUM):
            slave_wallets.append(LocalWallet.generate("okp4"))
        j = [{"private_key": wallet.signer().private_key} for wallet in slave_wallets]
        os.makedirs(os.path.join(os.getenv('HOME'), '.okp4'), mode=755, exist_ok=True)
        json.dump(j, open(os.path.join(os.getenv('HOME'), '.okp4', 'spam_wallets.json'), 'w+'))

    for wallet in slave_wallets:
        if ledger.query_bank_balance(wallet.address()) <= (1000000 / 2):
            print(f"send tokens to {wallet.address()}")
            t = ledger.prepare_send_tokens(destination=wallet.address(),
                                           amount=1000000,
                                           denom="uknow",
                                           sender=spam_wallet,
                                           account=spam_account,
                                           )
            r = ledger.broadcast_tx(t, True)
            spam_account.sequence += 1

    time.sleep(10)

    # create a logger
    logger = logging.getLogger('mylogger')

    # instanciate 1 thread per wallet
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as pool:
        results = pool.map(spam, slave_wallets)

    seq = 0
    now = datetime.now()
    amount = 1 * 10 ** 8
    break_block = 0
    # get the account info
    sequence = spam_account.sequence
    balance_1 = ledger.query_bank_balance(spam_wallet.address())
    while True:
        # get the balance of address_1
        print(f"sequence start: {sequence}")

        # check the balance is enought to not drain all our tcro
        if balance_1 >= 3000000:  # each loop cost 30TCRO
            # define last sequence number for the loop
            stop_at = sequence + 10000
            seq = sequence

            def call(seq) -> [int, Transaction]:
                spam_account.sequence = seq
                return seq, ledger.prepare_send_tokens(destination=spam_account.address,
                                                       amount=1,
                                                       denom="uknow",
                                                       sender=spam_wallet,
                                                       account=spam_account,
                                                       memo="stress test",
                                                       gas_limit=70000
                                                       )

            # r = [i for i in range(sequence, stop_at)]
            # with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as pool:
            #     # with ThreadPoolExecutor(max_workers=4) as pool:
            #     results = pool.map(call, r)
            # print(f"generated {len(r)} transaction")
            # results = [(seq, tx) for seq, tx in results]
            # results = sorted(results, key=lambda seq: seq[0])
            # for seq, tx in results:
            #     try:
            #         print(tx.tx.auth_info.signer_infos)
            #         sent_tx = broadcast_basic_transaction(ledger, tx)
            #     except BroadcastError as err:
            #         time.sleep(3)
            #         sent_tx = broadcast_basic_transaction(ledger, tx)
            #     time.sleep(0.001)
            for seq in range(sequence, stop_at):
                seq, tx = call(seq)
                sent_tx = broadcast_basic_transaction(ledger, tx)

            # update sequence start number
            sequence = seq
            # end for loop
            # sync_block(r)
            # send_object.set_mode("sync")
            time.sleep(5)
        else:
            print("no uknow left")
            withdraw_cmd = f"chain-maind tx distribution withdraw-all-rewards --from {address_1} -y --gas-prices 0.1basetcro --chain-id testnet-croeseid-2 --keyring-backend test --home /home/dpierret/.chain-maind"
            subprocess.check_output(withdraw_cmd, shell=True).decode("utf-8")
            sync_block(r)


if __name__ == "__main__":
    main()
