import json
from bottle import Bottle, response, request

from crankycoin.services.queue import Queue
from crankycoin.services.api_client import ApiClient
from crankycoin.models.enums import MessageType
from crankycoin.repository.peers import Peers
from crankycoin.repository.blockchain import Blockchain

permissioned_app = Bottle()


@permissioned_app.route('/connect/', method='POST')
def connect():
    api_client = ApiClient()
    peers = Peers()
    body = request.json
    host = body['host']
    if api_client.ping_status(host):
        peers.add_peer(host)
        response.status = 200
        return json.dumps({'success': True})
    return json.dumps({'success': False})


@permissioned_app.route('/inbox/', method='POST')
def post_to_inbox():
    # TODO: grab sender's IP
    # gets their IP but I'd rather have a non-spoofable method like passing in a header with your signed IP
    body = request.json
    host = request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')
    msg_type = body.get('type')
    if msg_type in MessageType:
        msg = {'host': host, 'type': msg_type, 'data': body.get('data')}
        Queue.enqueue(msg)
        response.status = 200
        return json.dumps({'success': True})
    response.status = 400
    return json.dumps({'success': False})


@permissioned_app.route('/blocks/start/<start_block_height:int>/end/<end_block_height:int>')
def get_blocks_inv(start_block_height, end_block_height):
    blockchain = Blockchain()
    if end_block_height - start_block_height > 500:
        end_block_height = start_block_height + 500
    blocks_inv = blockchain.get_hashes_range(start_block_height, end_block_height)
    if blocks_inv:
        return json.dumps({'block_hashes': blocks_inv})
    response.status = 404
    return json.dumps({'success': False, 'reason': 'Invalid block range'})


@permissioned_app.route('/transactions/block_hash/<block_hash>')
def get_transactions_index(block_hash):
    blockchain = Blockchain()
    transaction_inv = blockchain.get_transaction_hashes_by_block_hash(block_hash)
    if transaction_inv:
        return json.dumps({'tx_hashes': transaction_inv})
    response.status = 404
    return json.dumps({'success': False, 'reason': 'Transactions Not Found'})


@permissioned_app.route('/blocks/hash/<block_hash>')
def get_block_header_by_hash(block_hash):
    blockchain = Blockchain()
    block_header = blockchain.get_block_header_by_hash(block_hash)
    if block_header is None:
        response.status = 404
        return json.dumps({'success': False, 'reason': 'Block Not Found'})
    return json.dumps(block_header.to_dict())


@permissioned_app.route('/blocks/height/<height:int>')
def get_block_header_by_height(height):
    blockchain = Blockchain()
    if height == "latest":
        block_header = blockchain.get_tallest_block_header()
    else:
        block_header = blockchain.get_block_headers_by_height(height)
    if block_header is None:
        response.status = 404
        return json.dumps({'success': False, 'reason': 'Block Not Found'})
    return json.dumps(block_header.to_dict())
