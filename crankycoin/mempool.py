from multiprocessing import Lock
import sqlite3

from config import *


class Mempool(object):

    def __init__(self):
        self.mempool_lock = Lock()
        self.db_init()

    def db_init(self):
        with sqlite3.connect(config['user']['db']) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(unconfirmed_transactions)")
            if len(cursor.fetchall()) > 0:
                return
            sql = open('config/init_mempool.sql', 'r').read()
            cursor = conn.cursor()
            cursor.executescript(sql)
        return

    def get_all_unconfirmed_transactions(self):
        raise NotImplementedError

    def get_unconfirmed_transaction(self):
        raise NotImplementedError

    def get_unconfirmed_transactions_chunk(self, chunk_size=None):
        raise NotImplementedError

    def push_unconfirmed_transaction(self, transaction):
        raise NotImplementedError

    def remove_unconfirmed_transaction(self, transaction_hash):
        raise NotImplementedError

    def remove_unconfirmed_transactions(self, transactions):
        raise NotImplementedError


class MempoolMemory(object):

    def __init__(self):
        self.unconfirmed_transactions = []
        self.unconfirmed_transactions_map = {}
        self.unconfirmed_transactions_lock = Lock()

    def get_all_unconfirmed_transactions(self):
        return self.unconfirmed_transactions

    def get_all_unconfirmed_transactions_map(self):
        return self.unconfirmed_transactions_map

    def get_unconfirmed_transaction(self, tx_hash):
        return self.unconfirmed_transactions_map.get(tx_hash)

    def get_unconfirmed_transactions_chunk(self, chunk_size=None):
        self.unconfirmed_transactions_lock.acquire()
        try:
            if len(self.unconfirmed_transactions) != len(self.unconfirmed_transactions_map):
                self._synchronize_unconfirmed_transaction_map()
            if chunk_size is None or chunk_size > len(self.unconfirmed_transactions):
                transactions = self.get_all_unconfirmed_transactions()
            else:
                transactions = self.unconfirmed_transactions[-chunk_size:]
        finally:
            self.unconfirmed_transactions_lock.release()
        return transactions

    def push_unconfirmed_transaction(self, transaction):
        status = False
        self.unconfirmed_transactions_lock.acquire()
        try:
            if len(self.unconfirmed_transactions) != len(self.unconfirmed_transactions_map):
                self._synchronize_unconfirmed_transaction_map()
            if self.unconfirmed_transactions_map.get(transaction.tx_hash) is None:
                for t in self.unconfirmed_transactions:
                    if transaction.fee <= t.fee:
                        self.unconfirmed_transactions.insert(self.unconfirmed_transactions.index(t), transaction)
                        status = True
                        break
                if status is False:
                    self.unconfirmed_transactions.append(transaction)
                    status = True
                self.unconfirmed_transactions_map[transaction.tx_hash] = transaction
        finally:
            self.unconfirmed_transactions_lock.release()
        return status

    def remove_unconfirmed_transaction(self, transaction_hash):
        status = False
        self.unconfirmed_transactions_lock.acquire()
        try:
            if len(self.unconfirmed_transactions) != len(self.unconfirmed_transactions_map):
                self._synchronize_unconfirmed_transaction_map()
            transaction = self.unconfirmed_transactions_map.pop(transaction_hash, None)
            if transaction is not None:
                self.unconfirmed_transactions.remove(transaction)
                status = True
        finally:
            self.unconfirmed_transactions_lock.release()
        return status

    def remove_unconfirmed_transactions(self, transactions):
        self.unconfirmed_transactions_lock.acquire()
        try:
            if len(self.unconfirmed_transactions) != len(self.unconfirmed_transactions_map):
                self._synchronize_unconfirmed_transaction_map()
            for t in transactions:
                if self.unconfirmed_transactions_map.pop(t.tx_hash, None) is not None:
                    self.unconfirmed_transactions.remove(t)
        finally:
            self.unconfirmed_transactions_lock.release()
        return

    def _synchronize_unconfirmed_transaction_map(self):
        # this method does not acquire a lock.  It is assumed that the calling method will acquire the lock
        # ensure uniqueness
        self.unconfirmed_transactions = sorted(set(self.unconfirmed_transactions), key=lambda t: t.fee)
        # rebuild map
        self.unconfirmed_transactions_map = {t.tx_hash: t for t in self.unconfirmed_transactions}
        return
