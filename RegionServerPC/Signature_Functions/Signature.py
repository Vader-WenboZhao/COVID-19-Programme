from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
import base64


'''私钥签名公钥验证'''


# 使用公钥验证签名
def sign(message, pri_key_path):
    with open(pri_key_path) as f:
        key = f.read()
        pri_key = RSA.importKey(key)
        signer = PKCS1_signature.new(pri_key)
        digest = SHA.new()
        digest.update(message.encode("utf8"))
        sign = signer.sign(digest)
        signature = base64.b64encode(sign)
        # print(signature.decode('utf-8'))
        return signature


# 使用公钥验证签名

def verify(message, signature, pub_key_path):
    with open(pub_key_path) as f:
        key = f.read()
        pub_key = RSA.importKey(key)
        verifier = PKCS1_signature.new(pub_key)
        digest = SHA.new()
        digest.update(message.encode("utf8"))
        # print(verifier.verify(digest, base64.b64decode(signature)))
        return verifier.verify(digest, base64.b64decode(signature))

'''
sig = sign("需要加密的信息", '/Users/zhaowenbo/wilna305/Fang3/项目/Signature_Functions/private_a.rsa')
print(verify("需要加密的信息", sig, '/Users/zhaowenbo/wilna305/Fang3/项目/Signature_Functions/public_a.rsa'))
'''
