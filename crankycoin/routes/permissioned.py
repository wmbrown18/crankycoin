import json
from crankycoin import app


@app.route('/connect/', methods=['POST'])
def connect(self, request):
    body = json.loads(request.content.read())
    host = body['host']
    if self.ping_status(host):
        self.peers.add_peer(host)
        request.setResponseCode(202)
        return json.dumps({'success': True})
    return json.dumps({'success': False})


@app.route('/inbox/', methods=['POST'])
def post_to_inbox(self, request):
    # TODO: grab sender's IP
    # request.getClientIP() gets their IP but I'd rather have a non-spoofable method
    # like passing in a header with your signed IP
    body = json.loads(request.content.read())
    host = request.getClientIP()
    block_hashes = body.get('block_hashes')
    tx_hashes = body.get('tx_hashes')
    block_header = body.get('block_header')
    if block_hashes or tx_hashes or block_header:
        body['host'] = host
        self.queue.put(body)
        request.setResponseCode(200)
        return json.dumps({'success': True})
    request.setResponseCode(400)
    return json.dumps({'success': False})


@app.route('/blocks/start/<start_block_height>/end/<end_block_height>', methods=['GET'])
def get_blocks_inv(self, request, start_block_height, end_block_height):
    if int(end_block_height) - int(start_block_height) > 500:
        end_block_height = start_block_height + 500
    blocks_inv = self.blockchain.get_hashes_range(int(start_block_height), int(end_block_height))
    if blocks_inv:
        return json.dumps({'block_hashes': blocks_inv})
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Invalid block range'})


@app.route('/transactions/block_hash/<block_hash>', methods=['GET'])
def get_transactions_inv(self, request, block_hash):
    transaction_inv = self.blockchain.get_transaction_hashes_by_block_hash(block_hash)
    if transaction_inv:
        return json.dumps({'tx_hashes': transaction_inv})
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Transactions Not Found'})


@app.route('/blocks/hash/<block_hash>', methods=['GET'])
def get_block_header_by_hash(self, request, block_hash):
    block_header = self.blockchain.get_block_header_by_hash(block_hash)
    if block_header is None:
        request.setResponseCode(404)
        return json.dumps({'success': False, 'reason': 'Block Not Found'})
    return json.dumps(block_header.to_dict())


@app.route('/blocks/height/<height>', methods=['GET'])
def get_block_header_by_height(self, request, height):
    if height == "latest":
        block_header = self.blockchain.get_tallest_block_header()
    else:
        block_header = self.blockchain.get_block_headers_by_height(int(height))
    if block_header is None:
        request.setResponseCode(404)
        return json.dumps({'success': False, 'reason': 'Block Not Found'})
    return json.dumps(block_header.to_dict())
