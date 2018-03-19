import json
from bottle import Bottle

from crankycoin import logger, config
from crankycoin.services import Validator
from crankycoin.models import Transaction
from crankycoin.repository import Peers, Mempool, Blockchain

public_app = Bottle()

@public_app.route('/status/')
def get_status(request):
    return json.dumps(config['network'])


@public_app.route('/nodes/')
def get_nodes(request):
    peers = Peers()
    nodes = {
        "full_nodes": peers.get_all_peers()
    }
    return json.dumps(nodes)


@public_app.route('/unconfirmed_tx/<tx_hash>')
def get_unconfirmed_tx(request, tx_hash):
    mempool = Mempool()
    unconfirmed_transaction = mempool.get_unconfirmed_transaction(tx_hash)
    if unconfirmed_transaction:
        return json.dumps(unconfirmed_transaction.to_dict())
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Transaction Not Found'})


@public_app.route('/unconfirmed_tx/count')
def get_unconfirmed_transactions_count(request):
    mempool = Mempool()
    return json.dumps(mempool.get_unconfirmed_transactions_count())


@public_app.route('/unconfirmed_tx/')
def get_unconfirmed_transactions(request):
    mempool = Mempool()
    return json.dumps([transaction.to_dict()
                       for transaction in mempool.get_all_unconfirmed_transactions_iter()])


@public_app.route('/address/<address>/balance')
def get_balance(request, address):
    blockchain = Blockchain()
    return json.dumps(blockchain.get_balance(address))


@public_app.route('/address/<address>/transactions')
def get_transaction_history(request, address):
    blockchain = Blockchain()
    return json.dumps(blockchain.get_transaction_history(address))


@public_app.route('/transactions/<tx_hash>')
def get_transaction(request, tx_hash):
    blockchain = Blockchain()
    transaction = blockchain.get_transaction_by_hash(tx_hash)
    if transaction:
        return json.dumps(transaction.to_dict())
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Transaction Not Found'})


@public_app.route('/transactions/', method='POST')
def post_transactions(request):
    mempool = Mempool()
    validator = Validator()
    body = json.loads(request.content.read())
    transaction = Transaction.from_dict(body['transaction'])
    if transaction.tx_hash != body['transaction']['tx_hash']:
        logger.info("Invalid transaction hash: {} should be {}".format(body['transaction']['tx_hash'], transaction.tx_hash))
        request.setResponseCode(406)
        return json.dumps({'message': 'Invalid transaction hash'})
    if mempool.get_unconfirmed_transaction(transaction.tx_hash) is None \
            and validator.validate_transaction(transaction) \
            and mempool.push_unconfirmed_transaction(transaction):
        request.setResponseCode(200)
        return json.dumps({'success': True, 'tx_hash': transaction.tx_hash})
    request.setResponseCode(406)
    return json.dumps({'success': False, 'reason': 'Invalid transaction'})
