import coincurve
import json
import random
import requests

from crankycoin import Transaction, logger, NodeMixin, config, Peers


class Client(NodeMixin):

    __private_key__ = None
    __public_key__ = None

    def __init__(self, private_key=None):
        if private_key is not None:
            self.__private_key__ = coincurve.PrivateKey.from_hex(private_key)
        else:
            logger.info("No private key provided. Generating new key pair.")
            self.__private_key__ = coincurve.PrivateKey()
        self.__public_key__ = self.__private_key__.public_key
        super(Client, self).__init__()

    def get_public_key(self):
        return self.__public_key__.format(compressed=True).encode('hex')

    def get_private_key(self):
        return self.__private_key__.to_hex()

    def sign(self, message):
        return self.__private_key__.sign(message).encode('hex')

    def verify(self, signature, message, public_key=None):
        if public_key is not None:
            return coincurve.PublicKey(public_key.decode('hex')).verify(signature.decode('hex'), message)
        return self.__public_key__.verify(signature, message)

    def get_balance(self, address=None, node=None):
        if address is None:
            address = self.get_public_key()
        if node is None:
            node = random.sample(self.full_nodes, 1)[0]
        url = self.BALANCE_URL.format(node, self.FULL_NODE_PORT, address)
        try:
            response = requests.get(url)
            return response.json()
        except requests.exceptions.RequestException as re:
            pass
        return None

    def get_transaction_history(self, address=None, node=None):
        if address is None:
            address = self.get_public_key()
        if node is None:
            node = random.sample(self.full_nodes, 1)[0]
        url = self.TRANSACTION_HISTORY_URL.format(node, self.FULL_NODE_PORT, address)
        try:
            response = requests.get(url)
            return response.json()
        except requests.exceptions.RequestException as re:
            pass
        return None

    def create_transaction(self, to, amount, fee, prev_hash):
        transaction = Transaction(
            self.get_public_key(),
            to,
            amount,
            fee,
            prev_hash=prev_hash
        )
        transaction.sign(self.get_private_key())
        return self.broadcast_transaction(transaction)

    def check_peers(self):
        # Light client version of check peers
        if self.peers.get_peers_count() < self.MIN_PEERS:
            known_peers = self.find_known_peers()
            for peer in known_peers:
                if self.peers.get_peers_count() >= self.MIN_PEERS:
                    break

                status_url = self.STATUS_URL.format(peer, self.FULL_NODE_PORT)
                try:
                    response = requests.get(status_url)
                    if response.status_code == 200 and json.loads(response.json()) == config['network']:
                        self.peers.add_peer(peer)
                except requests.exceptions.RequestException as re:
                    pass
        return


if __name__ == "__main__":
    pass
