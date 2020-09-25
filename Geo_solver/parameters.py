import socket

PRI_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/private_Geo_solver.rsa'
PUB_KEY_PATH = '/Users/zhaowenbo/wilna305/Fang3/项目/Geo_solver/Signature_Functions/public_Geo_solver.rsa'
LOCATION = 'Dalian'
TIMERANGE = 60 # 1min

# sendAddr = ('127.0.0.1', 8081)
listenAddr = ('127.0.0.1', 8081)

addr_Shenzhen = ('127.0.0.1', 8082)
addr_Chengdu = ('127.0.0.1', 8083)
addr_Beijing = ('127.0.0.1', 8084)

sendSocket1 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket2 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sendSocket3 = socket.socket(socket.AF_INET,socket.SOCK_STREAM)


addrList = [(sendSocket1, addr_Shenzhen), (sendSocket2, addr_Chengdu), (sendSocket3, addr_Beijing)]
