import socket

PRI_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/private_Geo_solver.rsa'
PUB_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/public_Geo_solver.rsa'
LOCATION = 'Location_#1'


# region server 8061 (Shenzhen)
# fix device 1 8071
# fix device 2 8072
# fix device 3 8073

''' UDP '''

regionServerShenzhen = ('127.0.0.1', 8061)

myAddr = ('127.0.0.1', 8071)
