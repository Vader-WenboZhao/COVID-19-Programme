import socketserver
import threading
import time

# outdoor
# listenAddr = ('172.20.10.3', 8081)
# indoor
listenAddr = ('192.168.1.100', 8090)

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            print('waiting for connect')
            while True:
                self.data = self.request.recv(1024)
                print('address:', self.client_address)
                # self.request.send(self.data.upper())
                if not self.data:
                    continue
                print(self.data)
                continue

server = socketserver.ThreadingTCPServer(listenAddr, Handler)
server.serve_forever()
