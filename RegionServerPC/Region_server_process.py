import socketserver
import threading
import time

listenAddr = ('172.20.10.3', 8081)
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
