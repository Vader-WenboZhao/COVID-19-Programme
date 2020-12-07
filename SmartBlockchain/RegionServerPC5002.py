from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request
import json

BPSCARRESS = f'http://127.0.0.1:5000/'
HOST = '0.0.0.0'
PORT = 5002

class Smart_Blockchain:
    def __init__(self):
        self.chain = []
        self.nodes = set()


    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def smart_chain(self):
        """
        All nodes can receive the smart_chain
        """

        schain = None
        response = requests.get(BPSCARRESS + f'chain')

        if response.status_code == 200:
            chain = response.json()['chain']
            schain = chain

        # Replace our chain
        if schain:
            self.chain = schain
            return True

        return False



# Instantiate the Node
app = Flask(__name__)

# Instantiate the Smart_Blockchain
blockchain = Smart_Blockchain()


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/smart/chain', methods=['GET'])
def smart_chain():
    replaced = blockchain.smart_chain()

    if replaced:
        response = {
            'message': 'Smart chain update by bpsc',
            'smart chain': blockchain.chain,
            'length': len(blockchain.chain)
        }
    else:
        response = {
            'message': 'Unsuccessful: Please try again',
            'old chain': blockchain.chain,
            'length': len(blockchain.chain)
        }

    return jsonify(response), 200


@app.route('/newtrace', methods=['POST'])
def add_new_trace():
    values = request.get_json()

    required = ['pseudonym', 'timestamp', 'location', 'amount_send']
    if not all(k in values for k in required):
        return 'Missing values', 400

    pseudonym = values.get('pseudonym')
    timestamp = values.get('timestamp')
    location = values.get('location')
    amount_send = values.get('amount_send')

    if not isinstance(pseudonym, str) or not isinstance(timestamp, int) or not isinstance(location, str) or not isinstance(amount_send, int):
        return 'Wrong data type', 400

    data = {'pseudonym':pseudonym, 'timestamp':timestamp, 'location':location, 'amount_send':amount_send}

    try:
        requests.post(BPSCARRESS + f'traces/new', json=data)
    except BaseException:
        return "Failed to add new trace", 400

    return "Successfully added new trace", 201




if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)
