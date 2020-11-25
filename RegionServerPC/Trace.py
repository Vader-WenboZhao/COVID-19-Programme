import hashlib
import time
import json
from Signature_Functions import Signature


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
        trace_string = (str(self.pseudonym) + str(self.location) + str(self.timestamp)).encode()
        return hashlib.sha256(trace_string).hexdigest()


    def sign(self, private_key_path):
    # RSA sign the message
        self.signature = Signature.sign(str(self.getHash()), private_key_path)


    def verify(self, public_key_path):
        if self.pseudonym == "0":
            return True
        return Signature.verify(str(self.getHash()), self.signature, public_key_path)

'''
tra = Trace("123", "456", 10)
tra.sign(PRI_KEY_PATH)
print(tra.dictForm())
print(tra.verify(PUB_KEY_PATH))
'''
