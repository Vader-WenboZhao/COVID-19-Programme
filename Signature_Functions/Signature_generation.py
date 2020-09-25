from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_signature
import base64

random_generator = Random.new().read
rsa = RSA.generate(2048, random_generator)


private_key = rsa.exportKey()
with open("/Users/zhaowenbo/wilna305/Fang3/项目/Signature/private_a.rsa", 'wb') as f:
    f.write(private_key)

public_key = rsa.publickey().exportKey()
with open("/Users/zhaowenbo/wilna305/Fang3/项目/Signature/public_a.rsa", 'wb') as f:
    f.write(public_key)
