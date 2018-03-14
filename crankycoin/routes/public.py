import json
from crankycoin import app


@app.route('/status/', methods=['GET'])
def get_status(self, request):
    return json.dumps(config['network'])


@app.route('/nodes/', methods=['GET'])
def get_nodes(self, request):
    nodes = {
        "full_nodes": self.peers.get_all_peers()
    }
    return json.dumps(nodes)


@app.route('/unconfirmed_tx/<tx_hash>', methods=['GET'])
def get_unconfirmed_tx(self, request, tx_hash):
    unconfirmed_transaction = self.mempool.get_unconfirmed_transaction(tx_hash)
    if unconfirmed_transaction:
        return json.dumps(unconfirmed_transaction.to_dict())
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Transaction Not Found'})


@app.route('/unconfirmed_tx/count', methods=['GET'])
def get_unconfirmed_transactions_count(self, request):
    return json.dumps(self.mempool.get_unconfirmed_transactions_count())


@app.route('/unconfirmed_tx/', methods=['GET'])
def get_unconfirmed_transactions(self, request):
    return json.dumps([transaction.to_dict()
                       for transaction in self.mempool.get_all_unconfirmed_transactions_iter()])


@app.route('/address/<address>/balance', methods=['GET'])
def get_balance(self, request, address):
    return json.dumps(self.blockchain.get_balance(address))


@app.route('/address/<address>/transactions', methods=['GET'])
def get_transaction_history(self, request, address):
    return json.dumps(self.blockchain.get_transaction_history(address))


@app.route('/transactions/<tx_hash>', methods=['GET'])
def get_transaction(self, request, tx_hash):
    transaction = self.blockchain.get_transaction_by_hash(tx_hash)
    if transaction:
        return json.dumps(transaction.to_dict())
    request.setResponseCode(404)
    return json.dumps({'success': False, 'reason': 'Transaction Not Found'})


@app.route('/transactions/', methods=['POST'])
def post_transactions(self, request):
    body = json.loads(request.content.read())
    transaction = Transaction(
        body['transaction']['source'],
        body['transaction']['destination'],
        body['transaction']['amount'],
        body['transaction']['fee'],
        prev_hash=body['transaction']['prev_hash'],
        tx_type=body['transaction']['tx_type'],
        timestamp=body['transaction']['timestamp'],
        asset=body['transaction']['asset'],
        data=body['transaction']['data'],
        signature=body['transaction']['signature'])
    if transaction.tx_hash != body['transaction']['tx_hash']:
        logger.warn("Invalid transaction hash: {} should be {}".format(body['transaction']['tx_hash'], transaction.tx_hash))
        request.setResponseCode(406)
        return json.dumps({'message': 'Invalid transaction hash'})
    if self.mempool.get_unconfirmed_transaction(transaction.tx_hash) is None \
            and self.blockchain.validate_transaction(transaction) \
            and self.mempool.push_unconfirmed_transaction(transaction):
        request.setResponseCode(200)
        return json.dumps({'success': True, 'tx_hash': transaction.tx_hash})
    request.setResponseCode(406)
    return json.dumps({'success': False, 'reason': 'Invalid transaction'})
