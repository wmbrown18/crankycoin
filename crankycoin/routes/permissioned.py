import json
from bottle import Bottle

from crankycoin.services import Queue, ApiClient
from crankycoin.models import MessageType
from crankycoin.repository import Peers, Blockchain

permissioned_app = Bottle()


@permissioned_app.route('/connect/', method='POST')
def connect(request):
    api_client = ApiClient()
    peers = Peers()
    body = json.loads(request.content.read())
    host = body['host']
    if api_client.ping_status(host):
        peers.add_peer(host)
        request.setResponseCode(202)
        return json.dumps({'success': True})
    return json.dumps({'success': False})


@permissioned_app.route('/inbox/', method='POST')
def post_to_inbox(request):
    # TODO: grab sender's IP
    # request.getClientIP() gets their IP but I'd rather have a non-spoofable method
    # like passing in a header with your signed IP
    body = json.loads(request.content.read())
    host = request.getClientIP()
    msg_type = body.get('type')
    if msg_type in MessageType:
        body['host'] = host
        Queue.enqueue(body)
        request.setResponseCode(200)
        return json.dumps({'success': True})
    request.setResponseCode(400)
    return json.dumps({'success': False})


@permissioned_app.route('/blocks/start/<start_block_height>/end/<end_block_height>')
def get_blocks_inv(request, start_block_height, end_block_height):
    blockchain = Blockchain()
    if int(end_block_height) - int(start_block_height) > 500:
        end_block_height = start_block_height + 500
    blocks_inv = blockchain.get_hashes_range(int(start_block_height), int(end_block_height))
    if blocks_inv:
        return json.dumps({'block_hashes': blocks_inv})
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Invalid block range'})


@permissioned_app.route('/transactions/block_hash/<block_hash>')
def get_transactions_index(request, block_hash):
    blockchain = Blockchain()
    transaction_inv = blockchain.get_transaction_hashes_by_block_hash(block_hash)
    if transaction_inv:
        return json.dumps({'tx_hashes': transaction_inv})
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Transactions Not Found'})


@permissioned_app.route('/blocks/hash/<block_hash>')
def get_block_header_by_hash(request, block_hash):
    blockchain = Blockchain()
    block_header = blockchain.get_block_header_by_hash(block_hash)
    if block_header is None:
        request.setResponseCode(404)
        return json.dumps({'success': False, 'reason': 'Block Not Found'})
    return json.dumps(block_header.to_dict())


@permissioned_app.route('/blocks/height/<height>')
def get_block_header_by_height(request, height):
    blockchain = Blockchain()
    if height == "latest":
        block_header = blockchain.get_tallest_block_header()
    else:
        block_header = blockchain.get_block_headers_by_height(int(height))
    if block_header is None:
        request.setResponseCode(404)
        return json.dumps({'success': False, 'reason': 'Block Not Found'})
    return json.dumps(block_header.to_dict())
