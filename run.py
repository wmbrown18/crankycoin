#!/usr/bin/env python

from __future__ import print_function

import argparse
import hashlib
import requests
import sys
from getpass import getpass
from Cryptodome.Cipher import AES
from crankycoin import *

_PY3 = sys.version_info[0] > 2
if _PY3:
    raw_input = input


def client():
    helptext = '''
        Available commands:
        ===================
        balance <public key (optional)>
        send <destination> <amount> <fee>
        publickey
        privatekey
        history <public key (optional)>
        quit or exit
    '''
    encrypted = config['user']['encrypted_private_key']
    if encrypted is None:
        print("\n\nNo private key provided. A new wallet will be generated for you...\n\n")
        client = Client()
    else:
        passphrase = getpass("Enter passphrase: ")
        encrypted = encrypted.decode('hex')
        nonce = encrypted[0:16]
        tag = encrypted[16:32]
        ciphertext = encrypted[32:]
        hashedpass = hashlib.sha256(passphrase).digest()
        cipher = AES.new(hashedpass, AES.MODE_EAX, nonce)
        try:
            private_key = cipher.decrypt_and_verify(ciphertext, tag)
            client = Client(private_key)
        except ValueError as ve:
            logger.warn('Invalid passphrase')
            print("\n\nInvalid passphrase\n\n")
            sys.exit(1)

    while True:
        cmd = raw_input("{} ({}) wallet > ".format(config['network']['name'], config['network']['ticker_symbol']))
        cmd_split = cmd.split()
        try:
            if cmd_split[0] == "balance":
                if len(cmd_split) == 2:
                    print(client.get_balance(cmd_split[1]))
                else:
                    print(client.get_balance())
            elif cmd_split[0] == "send":
                if len(cmd_split) == 4:
                    print(client.create_transaction(cmd_split[1], float(cmd_split[2]), float(cmd_split[3])))
                else:
                    print("\nRequires destination, amount, fee\n")
            elif cmd_split[0] == "publickey":
                print(client.get_public_key())
            elif cmd_split[0] == "privatekey":
                print(client.get_private_key())
            elif cmd_split[0] == "history":
                if len(cmd_split) == 2:
                    print(client.get_transaction_history(cmd_split[1]))
                else:
                    print(client.get_transaction_history())
            elif cmd_split[0] in ("quit", "exit"):
                sys.exit(0)
            else:  # help
                print(helptext)
        except IndexError:
            pass


def full(mine=False):
    helptext = '''
        Available commands:
        ===================
        balance <public key (optional)>
        history <public key (optional)>
        getnodes
        getblock <index (optional)>
        getblocks <start index (optional)> <stop index (optional)>
        mempoolcount
        getmempool
        getunconfirmedtx <tx hash>
        quit or exit
    '''
    ip = config['user']['ip']
    public_key = config['user']['public_key']
    if ip is None or public_key is None:
        print("\n\npublic key and IP must be provided.\n\n")
        sys.exit(1)
    if(mine):
        print("\n\nmining node starting...\n\n")
        fullnode = FullNode(ip, public_key, mining=True)
    else:
        print("\n\nfull node starting...\n\n")
        fullnode = FullNode(ip, public_key)

    while True:
        cmd = raw_input("{} ({}) full node > ".format(config['network']['name'], config['network']['ticker_symbol']))
        cmd_split = cmd.split()
        try:
            if cmd_split[0] == "balance":
                if len(cmd_split) == 2:
                    url = fullnode.BALANCE_URL.format("localhost", fullnode.FULL_NODE_PORT, cmd_split[1])
                else:
                    url = fullnode.BALANCE_URL.format("localhost", fullnode.FULL_NODE_PORT, public_key)
                response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "history":
                if len(cmd_split) == 2:
                    url = fullnode.TRANSACTION_HISTORY_URL.format("localhost", fullnode.FULL_NODE_PORT, cmd_split[1])
                    response = requests.get(url)
                else:
                    url = fullnode.TRANSACTION_HISTORY_URL.format("localhost", fullnode.FULL_NODE_PORT, public_key)
                    response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "getnodes":
                url = fullnode.NODES_URL.format("localhost", fullnode.FULL_NODE_PORT)
                response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "getblock":
                if len(cmd_split) == 2:
                    url = fullnode.BLOCKS_URL.format("localhost", fullnode.FULL_NODE_PORT, cmd_split[1])
                else:
                    url = fullnode.BLOCKS_URL.format("localhost", fullnode.FULL_NODE_PORT, "latest")
                response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "getblocks":
                if len(cmd_split) == 3:
                    url = fullnode.BLOCKS_RANGE_URL.format("localhost", fullnode.FULL_NODE_PORT, cmd_split[1], cmd_split[2])
                else:
                    url = fullnode.BLOCKS_URL.format("localhost", fullnode.FULL_NODE_PORT, "")
                response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "mempoolcount":
                url = fullnode.TRANSACTIONS_URL.format("localhost", fullnode.FULL_NODE_PORT, "count")
                response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "getmempool":
                url = fullnode.TRANSACTIONS_URL.format("localhost", fullnode.FULL_NODE_PORT, "")
                response = requests.get(url)
                print(response.json())
            elif cmd_split[0] == "getunconfirmedtx":
                if len(cmd_split) == 2:
                    url = fullnode.TRANSACTIONS_URL.format("localhost", fullnode.FULL_NODE_PORT, cmd_split[1])
                    response = requests.get(url)
                    print(response.json())
                else:
                    print("\nRequires tx hash\n")
            elif cmd_split[0] in ("quit", "exit"):
                fullnode.shutdown()
                sys.exit(0)
            else:  # help
                print(helptext)
        except IndexError:
            pass


def main(argv):
    parser = argparse.ArgumentParser(description='Starts a ' + config['network']['name'] + ' node')
    parser.add_argument('mode', metavar='type', nargs='?', default=None, help='client | full | miner')
    args = parser.parse_args()
    if args.mode == "client":
        client()
    elif args.mode == "full":
        full()
    elif args.mode == "miner":
        full(mine=True)
    else:
        print("Node operation mode not specified")


if __name__ == "__main__":
    main(sys.argv[1:])
