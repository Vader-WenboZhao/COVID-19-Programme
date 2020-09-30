import hashlib
import json
import requests
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request
from Trace import Trace

DIFFICULTY = "0000"
BLOCKLENGTH = 1

class Blockchain(object):
    def __init__(self):
        ...
        self.nodes = set()
        # 用 set 来储存节点，避免重复添加节点.
        ...
        self.chain = []
        self.current_traces = []

        #创建创世区块
        # self.new_block(previous_hash=1,proof=100)

        # 统一各个节点的创世区块
        block = {
            'index':len(self.chain)+1,
            'timestamp':9999999999,
            'traces': [],
            'proof':100,
            'previous_hash':1,
        }

        self.chain.append(block)

    def register_node(self,address):
        """
        在节点列表中添加一个新节点
        :param address:
        :return:
        """
        prsed_url = urlparse(address)
        self.nodes.add(prsed_url.netloc)

    def valid_chain(self,chain):
        """
        确定一个给定的区块链是否有效
        :param chain:
        :return:
        """
        last_block = chain[0]
        current_index = 1

        while current_index<len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            # 检查block的散列是否正确
            if block['previous_hash'] != self.hash(last_block):
                return False
            # 检查工作证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
        return True


    def resolve_conflicts(self):
        """
        共识算法
        :return:
        """
        neighbours = self.nodes
        new_chain = None
        # 寻找最长链条
        max_length = len(self.chain)

        # 获取并验证网络中的所有节点的链
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # 检查长度是否长，链是否有效
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 如果发现一个新的有效链比当前的长，就替换当前的链
        if new_chain:
            self.chain = new_chain
            return True
        return False

    def new_block(self,proof,previous_hash=None, tmsp=None):
        """
        创建一个新的块并将其添加到链中
        :param proof: 由工作证明算法生成证明
        :param previous_hash: 前一个区块的hash值
        :return: 新区块
        """
        block = {
            'index':len(self.chain)+1,
            'timestamp':tmsp or time(),
            'traces':self.current_traces,
            'proof':proof,
            'previous_hash':previous_hash or self.hash(self.chain[-1]),
        }

        # 重置当前交易记录
        self.current_traces = []

        self.chain.append(block)
        return block

    def new_trace(self, pseudonym, ismine, location, pri_k_path):
        # 将新事务添加到事务列表中
        newTrace = Trace(pseudonym, location, int(time()))
        if not ismine:
            newTrace.sign(pri_k_path)
        self.current_traces.append(str(newTrace.dictForm()))

        return  self.last_block['index'] + 1, newTrace

    def add_trace(self, trace):
        newTrace = trace
        self.current_traces.append(str(newTrace.dictForm()))
        return True


    @staticmethod
    def hash(block):
        """
        给一个区块生成 SHA-256 值
        :param block:
        :return:
        """
        # 必须确保这个字典（区块）是经过排序的，否则将会得到不一致的散列
        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    def deleteOldBlock(self):
        while(True):
            #  创建区块超过十四天
            if int(time()) - self.chain[0]['timestamp'] >= 1209600:
                self.chain.remove(self.chain[0])
                continue
            else:
                break


    @property
    def last_block(self):
        # 返回链中的最后一个块
        return self.chain[-1]


    def proof_of_work(self,last_proof):
        # 工作算法的简单证明
        proof = 0
        while self.valid_proof(last_proof,proof) is False:
            proof +=1
        return proof

    @staticmethod
    def valid_proof(last_proof,proof):
        # 验证证明
        global DIFFICULTY
        guess =  f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == DIFFICULTY
