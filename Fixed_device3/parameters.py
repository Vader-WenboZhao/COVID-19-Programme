import socket

PRI_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/private_Geo_solver.rsa'
PUB_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/public_Geo_solver.rsa'
LOCATION = 'Beijing'

Geo_solver = ('127.0.0.1', 8081)

listenAddr = ('127.0.0.1', 8084)

diagnostician1 = ('127.0.0.1', 8090)

addr_Shenzhen = ('127.0.0.1', 8082)
addr_Chengdu = ('127.0.0.1', 8083)

sendSocket1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket3 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket4 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)


addrList = [(sendSocket1, Geo_solver), (sendSocket2, addr_Shenzhen), (sendSocket3, addr_Chengdu), (sendSocket4, diagnostician1)]
