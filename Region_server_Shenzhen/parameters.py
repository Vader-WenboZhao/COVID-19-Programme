import socket

PRI_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/private_Geo_solver.rsa'
PUB_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/public_Geo_solver.rsa'
LOCATION = 'Shenzhen'

# geo server 8081
# Shenzhen 8082
# Chengdu 8083
# Beijing 8084
# region sever 8085
# diagnostician1 8090

Geo_solver = ('127.0.0.1', 8081)

listenAddr = ('127.0.0.1', 8082)

diagnostician1 = ('127.0.0.1', 8090)

addr_Chengdu = ('127.0.0.1', 8083)
addr_Beijing = ('127.0.0.1', 8084)

udpServerAddr = ('127.0.0.1', 8061)

sendSocket1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket3 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket4 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)


addrList = [(sendSocket1, Geo_solver), (sendSocket2, addr_Chengdu), (sendSocket3, addr_Beijing), (sendSocket4, diagnostician1)]
