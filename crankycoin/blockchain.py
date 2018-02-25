from math import floor
from multiprocessing import Lock
import sqlite3

from config import *
from crankycoin import BlockHeader, Block
from crankycoin import Transaction
from errors import *


class Blockchain(object):

    INITIAL_COINS_PER_BLOCK = config['network']['initial_coins_per_block']
    HALVING_FREQUENCY = config['network']['halving_frequency']
    MAX_TRANSACTIONS_PER_BLOCK = config['network']['max_transactions_per_block']
    MINIMUM_HASH_DIFFICULTY = config['network']['minimum_hash_difficulty']
    TARGET_TIME_PER_BLOCK = config['network']['target_time_per_block']
    DIFFICULTY_ADJUSTMENT_SPAN = config['network']['difficulty_adjustment_span']
    SIGNIFICANT_DIGITS = config['network']['significant_digits']

    def __init__(self):
        self.blocks_lock = Lock()
        self.db_init()

    def db_init(self):
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(blocks)")
            if len(cursor.fetchall()) > 0:
                return
            sql = open('config/init.sql', 'r').read()
            cursor = conn.cursor()
            cursor.executescript(sql)
        return

    def _check_hash_and_hash_pattern(self, block):
        hash_difficulty = self.calculate_hash_difficulty()
        if block.current_hash[:hash_difficulty].count('0') != hash_difficulty:
            raise InvalidHash(block.height, "Incompatible Block Hash: {}".format(block.current_hash))
        return

    def _check_height_and_previous_hash(self, block):
        latest_block = self.get_latest_block_header()
        if latest_block.height != block.height - 1:
            raise ChainContinuityError(block.height, "Incompatible block height: {}".format(block.height-1))
        if latest_block.current_hash != block.block_header.previous_hash:
            raise ChainContinuityError(block.height, "Incompatible block hash: {} and hash: {}".format(block.height-1, block.block_header.previous_hash))
        return

    def _check_transactions_and_block_reward(self, block):
        # transactions : list of transactions
        # transaction : Transaction(source, destination, amount, fee, signature)
        reward_amount = self.get_reward(block.height)
        payers = dict()
        for transaction in block.transactions[1:0]:
            if self.find_duplicate_transactions(transaction.tx_hash):
                raise InvalidTransactions(block.height, "Transactions not valid.  Duplicate transaction detected")
            if not transaction.verify():
                raise InvalidTransactions(block.height, "Transactions not valid.  Invalid Transaction signature")
            if transaction.source in payers:
                payers[transaction.source] += transaction.amount + transaction.fee
            else:
                payers[transaction.source] = transaction.amount + transaction.fee
            reward_amount += transaction.fee
        for key in payers:
            balance = self.get_balance(key)
            if payers[key] > balance:
                raise InvalidTransactions(block.height, "Transactions not valid.  Insufficient funds")
        # first transaction is coinbase
        reward_transaction = block.transactions[0]
        if reward_transaction.amount != reward_amount or reward_transaction.source != "0":
            raise InvalidTransactions(block.height, "Transactions not valid.  Incorrect block reward")
        return

    def validate_block(self, block):
        # verify genesis block integrity
        try:
            # current hash of data is correct and hash satisfies pattern
            self._check_hash_and_hash_pattern(block)
            # block height is correct and previous hash is correct
            self._check_height_and_previous_hash(block)
            # block reward is correct based on block height and halving formula
            self._check_transactions_and_block_reward(block)
        except BlockchainException as bce:
            logger.warning("Validation Error (block id: %s): %s", bce.height, bce.message)
            return False
        return True

    def validate_transaction(self, transaction):
        if self.find_duplicate_transactions(transaction.tx_hash):
            logger.warn('Transaction not valid.  Replay transaction detected: {}'.format(transaction.tx_hash))
            return False
        if not transaction.verify():
            logger.warn('Transaction not valid.  Invalid transaction signature: {}'.format(transaction.tx_hash))
            return False
        balance = self.get_balance(transaction.source)
        if transaction.amount + transaction.fee > balance:
            logger.warn('Transaction not valid.  Insufficient funds: {}'.format(transaction.tx_hash))
            return False
        return True

    def alter_chain(self, blocks):
        # TODO: Deprecate?
        fork_start = blocks[0].height
        alternate_blocks = self.blocks[0:fork_start]
        alternate_blocks.extend(blocks)
        alternate_chain = Blockchain(alternate_blocks)

        status = False
        if alternate_chain.get_height() > self.get_height():
            self.blocks_lock.acquire()
            try:
                self.blocks = alternate_blocks
                status = True
            finally:
                self.blocks_lock.release()
        return status

    def add_block(self, block, validate=True):
        status = False
        if not validate or self.validate_block(block):
            sql_strings = list()
            sql_strings.append('INSERT INTO blocks (hash, prevhash, merkleRoot, height, nonce, timestamp, version)\
                VALUES ({}, {}, {}, {}, {}, {}, {})'.format(block.current_hash, block.block_header.previous_hash, 
                    block.block_header.merkle_root, block.height, block.block_header.nonce, block.block_header.timestamp, 
                    block.block_header.version))
            for transaction in block.transactions:
                sql_strings.append('INSERT INTO transactions (hash, src, dest, amount, fee, timestamp, signature, type,\
                    blockHash, asset, data) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})'.format(
                        transaction.tx_hash, transaction.source, transaction.destination, transaction.amount,
                        transaction.fee, transaction.timestamp, transaction.signature, transaction.tx_type,
                        block.current_hash, transaction.asset, transaction.data))
            try:
                with sqlite3.connect(config['user']['db']) as conn:
                    cursor = conn.cursor()
                    for sql in sql_strings:
                        cursor.execute(sql)
                    status = True
            except sqlite3.OperationalError as err:
                logger.error("Database Error: ", err.message)
        return status

    def get_transaction_history(self, address):
        # TODO: convert this to return a generator
        transactions = []
        sql = 'SELECT * FROM transactions WHERE src={} OR dest={}'.format(address, address)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for transaction in cursor:
                transactions.append(Transaction(transaction[1], transaction[2], transaction[3], transaction[4],
                                    tx_type=transaction[7], timestamp=transaction[5], tx_hash=transaction[0],
                                    signature=transaction[6], asset=transaction[8], data=transaction[9]))
        return transactions

    def get_transactions_by_block_hash(self, block_hash):
        transactions = []
        sql = 'SELECT * FROM transactions WHERE blockHash='.format(block_hash)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for transaction in cursor:
                transactions.append(Transaction(transaction[1], transaction[2], transaction[3], transaction[4],
                                    tx_type=transaction[7], timestamp=transaction[5], tx_hash=transaction[0],
                                    signature=transaction[6], asset=transaction[8], data=transaction[9]))
        return transactions

    def get_transaction_by_hash(self, transaction_hash):
        sql = 'SELECT * FROM transactions WHERE hash={}'.format(transaction_hash)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            transaction = cursor.fetchone()
        return Transaction(transaction[1], transaction[2], transaction[3], transaction[4], tx_type=transaction[7],
                           timestamp=transaction[5], tx_hash=transaction[0], signature=transaction[6],
                           asset=transaction[8], data=transaction[9])

    def get_balance(self, address, asset=None):
        if asset is None:
            asset = '29bb7eb4fa78fc709e1b8b88362b7f8cb61d9379667ad4aedc8ec9f664e16680'
        balance = 0
        sql = 'SELECT src, dest, amount, fee FROM transactions WHERE (src={} OR dest={}) AND asset={} AND type < 3'\
            .format(address, address, asset)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for transaction in cursor:
                if transaction[0] == address:
                    balance -= transaction[2] + transaction[3]
                else:
                    balance += transaction[2]
        return balance

    def find_duplicate_transactions(self, transaction_hash):
        sql = 'SELECT COUNT(*) FROM transactions WHERE hash={}'.format(transaction_hash)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            if count > 0:
                return True
        return False

    def calculate_hash_difficulty(self, height=None):
        if height is None:
            block = self.get_latest_block_header()[0]
            height = block.height
        else:
            block = self.get_block_header_by_height(height)[0]

        if block.height > self.DIFFICULTY_ADJUSTMENT_SPAN:
            block_delta = self.get_block_header_by_height(height - self.DIFFICULTY_ADJUSTMENT_SPAN)
            timestamp_delta = block.block_header.timestamp - block_delta.block_header.timestamp
            # blocks were mined quicker than target
            if timestamp_delta < (self.TARGET_TIME_PER_BLOCK * self.DIFFICULTY_ADJUSTMENT_SPAN):
                return block.hash_difficulty + 1
            # blocks were mined slower than target
            elif timestamp_delta > (self.TARGET_TIME_PER_BLOCK * self.DIFFICULTY_ADJUSTMENT_SPAN):
                return block.hash_difficulty - 1
            # blocks were mined within the target time window
            return block.hash_difficulty
        # not enough blocks were mined for an adjustment
        return self.MINIMUM_HASH_DIFFICULTY

    def get_reward(self, height):
        precision = pow(10, self.SIGNIFICANT_DIGITS)
        reward = self.INITIAL_COINS_PER_BLOCK
        for i in range(1, ((height / self.HALVING_FREQUENCY) + 1)):
            reward = floor((reward / 2.0) * precision) / precision
        return reward

    def get_height(self):
        sql = 'SELECT MAX(height) FROM blocks'
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            height = cursor.fetchone()[0]
        return height

    def get_latest_block_header(self):
        block_headers = []
        sql = 'SELECT * FROM blocks WHERE height = (SELECT MAX(height) FROM blocks)'
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for block in cursor:
                block_headers.append(BlockHeader(block[1], block[2], block[5], block[4], block[6]))
        return block_headers

    def get_block_header_by_height(self, height):
        block_headers = []
        sql = 'SELECT * FROM blocks WHERE height={}'.format(height)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for block in cursor:
                block_headers.append(BlockHeader(block[1], block[2], block[5], block[4], block[6]))
        return block_headers

    def get_block_header_by_hash(self, block_hash):
        sql = 'SELECT * FROM blocks WHERE hash={}'.format(block_hash)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            block = cursor.fetchone()
        return BlockHeader(block[1], block[2], block[5], block[4], block[6])

    def get_all_block_headers_iter(self):
        sql = 'SELECT * FROM blocks'
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for block in cursor:
                yield BlockHeader(block[1], block[2], block[5], block[4], block[6])

    def get_block_headers_range_iter(self, start_height, stop_height):
        sql = 'SELECT * FROM blocks WHERE height >= {} AND height <= {} ORDER BY height ASC'\
            .format(start_height, stop_height)
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for block in cursor:
                yield BlockHeader(block[1], block[2], block[5], block[4], block[6])

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other


if __name__ == "__main__":
    pass
