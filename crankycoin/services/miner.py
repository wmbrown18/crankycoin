import time

from crankycoin.models import Block, Transaction
from crankycoin.repository import Blockchain, Mempool
from crankycoin import config


class Miner(object):

    MAX_TRANSACTIONS_PER_BLOCK = config['network']['max_transactions_per_block']

    def __init__(self):
        self.blockchain = Blockchain()
        self.mempool = Mempool()

    def mine_block(self, reward_address):
        latest_block = self.blockchain.get_tallest_block_header()
        new_block_id = latest_block.index + 1
        previous_hash = latest_block.current_hash

        transactions = self.mempool.get_unconfirmed_transactions_chunk(self.MAX_TRANSACTIONS_PER_BLOCK)
        if len(transactions) > 0:
            fees = sum(t.fee for t in transactions)
        else:
            fees = 0

        # coinbase
        coinbase = Transaction(
            "0",
            reward_address,
            self.blockchain.get_reward(new_block_id) + fees,
            0,
            "0"
        )
        transactions.insert(0, coinbase)

        timestamp = int(time.time())
        i = 0
        block = Block(new_block_id, transactions, previous_hash, timestamp)

        while block.block_header.hash_difficulty < self.blockchain.calculate_hash_difficulty():
            latest_block = self.blockchain.get_tallest_block_header()
            if latest_block.index >= new_block_id or latest_block.current_hash != previous_hash:
                # Next block in sequence was mined by another node.  Stop mining current block.
                return None
            i += 1
            block.block_header.nonce = i
        return block
