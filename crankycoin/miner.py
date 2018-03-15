import logging
import multiprocessing as mp
import time

from crankycoin.models import Block, Transaction
from crankycoin.repository import Blockchain, Mempool
from crankycoin import config, logger


class Miner(object):

    MAX_TRANSACTIONS_PER_BLOCK = config['network']['max_transactions_per_block']

    def __init__(self, reward_address, queue):
        mp.log_to_stderr()
        mp_logger = mp.get_logger()
        mp_logger.setLevel(logging.DEBUG)
        self.reward_address = reward_address
        self.queue = queue
        self.blockchain = Blockchain()
        self.mempool = Mempool()
        self.miner_process = mp.Process(target=self.mine, args=[self.queue])

    def start(self):
        logger.debug("mining process starting with reward address %s...", self.reward_address)
        self.miner_process.start()

    def shutdown(self):
        logger.debug("mining process with reward address %s shutting down...", self.reward_address)
        self.miner_process.terminate()

    def mine(self, queue):
        while True:
            block = self.mine_block()
            if not block:
                continue
            queue.put({"block": block})
            logger.info("Block {} found with hash {} and nonce {}"
                        .format(block.height, block.block_header.hash, block.block_header.nonce))
            # if self.blockchain.add_block(block):
            #     self.mempool.remove_unconfirmed_transactions(block.transactions[1:])
            #     self.broadcast_block_inv(block.block_header.hash)
        return

    def mine_block(self):
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
            self.reward_address,
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
