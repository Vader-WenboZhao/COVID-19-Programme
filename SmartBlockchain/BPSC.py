import hashlib
import json
from time import time
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request


IPADDRESS = f'http://127.0.0.1:5000/'
HOST = '0.0.0.0'
PORT = 5000


class Smart_Blockchain:
    def __init__(self):
        self.current_traces = []
        self.chain = []
        self.nodes = set()

        # Create the genesis block
        self.new_block(previous_hash='1')


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
        response = requests.get(IPADDRESS + f'chain')

        if response.status_code == 200:
            chain = response.json()['chain']
            schain = chain

        # Replace our chain
        if schain:
            self.chain = schain
            return True

        return False


    def new_block(self, previous_hash):
        """
        Create a new Block in the Smart Blockchain
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'traces': self.current_traces,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of traces
        self.current_traces = []

        self.chain.append(block)
        return block


    def new_trace(self, name, time, loca):
        """
        Creates a new trace to go into the next mined Block
        :param sender: Address of the Sender
        :param bpsc: Address of the Smart contract (bpsc)
        :param recipient: Address of the Recipient
        :return: The index of the Block that will hold this trace
        """
        self.current_traces.append({
            'pseudonym': name,
            'timestamp': time,
            'location': loca,
        })

        return self.last_block['index'] + 1


    @property
    def last_block(self):
        return self.chain[-1]


    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


# Instantiate the Node
app = Flask(__name__)

# Instantiate the Smart_Blockchain
blockchain = Smart_Blockchain()
riskyPseudonyms = set()

# 区块链操作

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'traces': block['traces'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/traces/new', methods=['POST'])
def new_trace():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['pseudonym', 'timestamp', 'location']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new trace
    index = blockchain.new_trace(values['pseudonym'], values['timestamp'], values['location'])

    response = {'message': f'trace will be added to Block {index}'}

    last_block = blockchain.last_block

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'traces': block['traces'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 201


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



# 风险名单操作

@app.route('/risky/names', methods=['GET'])
def get_risky():
    global riskyPseudonyms
    response = {
    # set不能Json化
        'riskyPseudonyms': list(riskyPseudonyms)
    }

    return jsonify(response), 200


@app.route('/risky/add', methods=['POST'])
def add_risky():
    global riskyPseudonyms

    values = request.get_json()

    name = values.get('riskyName')
    if not isinstance(name, str):
        return "Error: Please supply a valid pseudonym", 400

    riskyPseudonyms.add(name)

    return "Added successfully", 201


@app.route('/risky/delete', methods=['POST'])
def delete_risky():
    global riskyPseudonyms

    values = request.get_json()

    name = values.get('riskyName')
    if not isinstance(name, str):
        return "Error: Please supply a valid pseudonym", 400

    if riskyPseudonyms.__contains__(name):
        riskyPseudonyms.remove(name)
        return "Deleted successfully", 201
    else:
        return "Deleted successfully", 201



if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=PORT, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host=HOST, port=port)
