import hashlib
import ubinascii
import crypto
from hashlib import sha512
import json



def byteToHex(bytes):
    return ubinascii.hexlify(bytes)

def getHexHashStr(str):
    sha256 = hashlib.sha256()
    sha256.update(str.encode('utf-8'))
    byteResult = sha256.digest()
    result = byteToHex(byteResult)
    return result

def stringify(newTrace):
    if type(newTrace) == type([]):
        resultList = []
        for tran in newTrace:
            resultList.append(tran.__dict__)
        return str(resultList)
    elif type(newTrace) == type(''):
        return newTrace
    else:
        return str(newTrace.__dict__)



class Trace:
    def __init__(self, pseudonym, location, timestamp, signature=None):
        self.pseudonym = pseudonym
        self.location = location
        self.timestamp = timestamp
        self.signature = signature

    def printInfo(self):
        print(self.__dict__)

    def dictForm(self):
        return self.__dict__

    def getHash(self):
        return getHexHashStr(str(self.pseudonym) + str(self.location) + str(self.timestamp))

    '''
    def getHash(self):
        trace_string = (str(self.pseudonym) + str(self.location) + str(self.timestamp)).encode()
        return hashlib.sha256(trace_string).hexdigest()
    '''

    def sign(self, private_key_path):
        pri_key_f = open(private_key_path)
        pri_key = pri_key_f.read()
        pri_key_f.close()
        self.signature = crypto.generate_rsa_signature(str(self.getHash()), pri_key, pers="my_pers_string")
        # self.signature = Signature.sign(str(self.getHash()), private_key_path)


    '''
    def sign(self, private_key_path):
    # RSA sign the message
        self.signature = Signature.sign(str(self.getHash()), private_key_path)
    '''


    # Lopy4设备上舍弃验签功能
    '''
    def verify(self, public_key_path):
        if self.pseudonym == "0":
            return True
        return Signature.verify(str(self.getHash()), self.signature, public_key_path)
    '''

'''
tra = Trace("123", "456", 10)
tra.sign(PRI_KEY_PATH)
print(tra.dictForm())
print(tra.verify(PUB_KEY_PATH))
'''
