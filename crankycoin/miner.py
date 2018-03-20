import logging
import multiprocessing as mp
import time

from crankycoin.models.block import Block
from crankycoin.models.transaction import Transaction
from crankycoin.models.enums import MessageType
from crankycoin.repository.blockchain import Blockchain
from crankycoin.repository.mempool import Mempool
from crankycoin.services.queue import Queue
from crankycoin import config, logger


class Miner(object):

    HOST = config['user']['ip']
    REWARD_ADDRESS = config['user']['public_key']
    MAX_TRANSACTIONS_PER_BLOCK = config['network']['max_transactions_per_block']
    miner_process = None

    def __init__(self):
        mp.log_to_stderr()
        mp_logger = mp.get_logger()
        mp_logger.setLevel(logging.DEBUG)
        self.blockchain = Blockchain()
        self.mempool = Mempool()

    def start(self):
        logger.debug("mining process starting with reward address %s...", self.REWARD_ADDRESS)
        self.miner_process = mp.Process(target=self.mine)
        self.miner_process.start()

    def shutdown(self):
        logger.debug("mining process with reward address %s shutting down...", self.REWARD_ADDRESS)
        self.miner_process.terminate()

    def mine(self):
        while True:
            block = self.mine_block()
            if not block:
                continue
            logger.info("Block {} found at height {} and nonce {}"
                        .format(block.block_header.hash, block.height, block.block_header.nonce))
            if self.blockchain.add_block(block):
                self.mempool.remove_unconfirmed_transactions(block.transactions[1:])
                Queue.enqueue({"host": self.HOST, "type": MessageType.BLOCK_HEADER, "data": block})
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
            self.REWARD_ADDRESS,
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
