from enum import Enum


class MessageType(Enum):

    BLOCK_HEADER = 1
    BLOCK_INV = 2
    UNCONFIRMED_TRANSACTION = 3
    TRANSACTION_INV = 4
