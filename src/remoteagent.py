#coding=utf8
#siddontang@gmail.com

import argparse
import sys
import socket
import time

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

from baseagent import BaseAgent
from misc import AgentAction

MAX_READ_BYTES = 1024 * 1024

def parseArgs():
    parser = argparse.ArgumentParser(description = 'Agent for destination server and relay server')
    parser.add_argument('--relay', metavar = 'host[:port]',
                        help = 'relay server')
    parser.add_argument('--relay-user', '-U', dest = 'user', 
                        metavar = 'username:[password]',
                        required = True, 
                        help = 'set relay user and password')
    parser.add_argument('--server', '-S', dest = 'server', 
                        metavar = 'host:port', required = True,
                        help = 'destination server')    
    parser.add_argument('--version', action='version', version='0.1')
    args = parser.parse_args()

    return args

class ClientAgent(BaseAgent):
    def __init__(self, config):
        BaseAgent.__init__(self, config, 'remote')

    def start(self):
        self._requestTunnel()

    def handleRecvData(self, data):
        self._log.info('handleRecvData %d' % len(data))

        if self._stream.closed():
            self._log.warning('stream is closed')
            return

        self._stream.write(data)

    def handleRecvError(self, data):
        self._log.error('client agent error %s, close stream too!' % (data))
        if not self._stream.closed():
            self._stream.set_close_callback(None)
            self._stream.close()

    def handleRecvConnect(self, data):
        self._connectServer()

    def _requestTunnel(self):
        request = self.buildRequest('/tunnel', method = 'POST', body = '')

        def callback(response):
            if response.error:
                self._log.error('requestTunnel Error %s, exit!' % response.error)
                sys.exit(2)
            else:
                self._log.warning('requestTunnel ok')

                print 'tunnel id : ', int(response.body)

                self._tunnel = int(response.body)

                self.recvRelayData()

                self._keepAlive()

        self._client.fetch(request, callback)

    def _keepAlive(self):
        def _keep():
            request = self.buildRequest('/tunnel', method = 'PUT', body = '')

            def callback(response):
                if response.error:
                    self._log.error('keepAlive Error %s' % response.error)

            self._client.fetch(request, callback)

            IOLoop.instance().add_timeout(int(time.time()) + 120, _keep)

        IOLoop.instance().add_timeout(int(time.time()) + 120, _keep)

    def _connectServer(self):
        host, port = self._config.server.split(':')
        port = int(port)

        def onConnected():
            self._log.info('connect server ok')
            self._recvServerData()

            self.recvRelayData()

        def onClose():
            self._log.error('connection was closed!')
            self.sendRelayData(action = AgentAction.Error, 
                               data = 'connectionClosed')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stream = IOStream(s)

        self._stream.set_close_callback(onClose)
        self._stream.connect((host, port), onConnected)

    def _recvServerData(self):
        def onStreaming(data):
            self.sendRelayData(AgentAction.Stream, data)

            self._stream.read_bytes(MAX_READ_BYTES, None, onStreaming)

        self._stream.read_bytes(MAX_READ_BYTES, None, onStreaming)

def main():
    app = ClientAgent(parseArgs())
    app.start()

    IOLoop.instance().start()

if __name__ == '__main__':
    main()
