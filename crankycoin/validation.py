from config import *
from errors import *


class Validation(object):

    def __init__(self, blockchain, mempool):
        self.blockchain = blockchain
        self.mempool = mempool

    def check_hash_and_hash_pattern(self, block):
        hash_difficulty = self.blockchain.calculate_hash_difficulty(block.height)
        if block.block_header.hash[:hash_difficulty].count('0') != hash_difficulty:
            raise InvalidHash(block.height, "Incompatible Block Hash: {}".format(block.current_hash))
        return

    def check_height_and_previous_hash(self, block):
        previous_block = self.blockchain.get_block_header_by_hash(
            block.block_header.previous_hash)
        if previous_block is None:
            raise ChainContinuityError(block.height, "Incompatible block hash: {} and hash: {}"
                                       .format(block.height-1, block.block_header.previous_hash))
        previous_block_header, previous_block_branch, previous_block_height = previous_block
        if previous_block_height != block.height - 1:
            raise ChainContinuityError(block.height, "Incompatible block height: {}".format(block.height-1))
        return

    def check_transactions_and_block_reward(self, block):
        reward_amount = self.blockchain.get_reward(block.height)
        payers = dict()
        for transaction in block.transactions[1:0]:
            if self.blockchain.find_duplicate_transactions(transaction.tx_hash):
                raise InvalidTransactions(block.height, "Transactions not valid.  Duplicate transaction detected")
            if not transaction.verify():
                raise InvalidTransactions(block.height, "Transactions not valid.  Invalid Transaction signature")
            if transaction.source in payers:
                payers[transaction.source] += transaction.amount + transaction.fee
            else:
                payers[transaction.source] = transaction.amount + transaction.fee
            reward_amount += transaction.fee
        for key in payers:
            balance = self.blockchain.get_balance(key)
            if payers[key] > balance:
                raise InvalidTransactions(block.height, "Transactions not valid.  Insufficient funds")
        # first transaction is coinbase
        reward_transaction = block.transactions[0]
        if reward_transaction.amount != reward_amount or reward_transaction.source != "0":
            raise InvalidTransactions(block.height, "Transactions not valid.  Incorrect block reward")
        return

    def validate_block(self, block):
        try:
            # current hash of data is correct and hash satisfies pattern
            self.check_hash_and_hash_pattern(block)
            # block height is correct and previous hash is correct
            self.check_height_and_previous_hash(block)
            # block reward is correct based on block height and halving formula
            self.check_transactions_and_block_reward(block)
        except BlockchainException as bce:
            logger.warning("Validation Error (block id: %s): %s", block.height, bce.message)
            return False
        return True

    def validate_transaction(self, transaction):
        if self.blockchain.find_duplicate_transactions(transaction.tx_hash):
            logger.warn('Transaction not valid.  Double-spend detected: {}'.format(transaction.tx_hash))
            return False
        if not transaction.verify():
            logger.warn('Transaction not valid.  Invalid transaction signature: {}'.format(transaction.tx_hash))
            return False
        balance = self.blockchain.get_balance(transaction.source)
        if transaction.amount + transaction.fee > balance:
            logger.warn('Transaction not valid.  Insufficient funds: {}'.format(transaction.tx_hash))
            return False
        return True


if __name__ == "__main__":
    pass
