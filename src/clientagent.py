#coding=utf8
#siddontang@gmail.com

import argparse
import sys

from tornado.ioloop import IOLoop

from baseagent import BaseAgent
from misc import AgentAction

MAX_READ_BYTES = 1024 * 1024

def parseArgs():
    parser = argparse.ArgumentParser(description = 'Agent for user client application and relay server')
    parser.add_argument('--port', '-p', dest = 'port',
                        metavar = 'N', type = int,
                        help = 'listen port for application connect')
    parser.add_argument('--relay', metavar = 'host[:port]',
                        help = 'relay server')
    parser.add_argument('--relay-user', '-U', dest = 'user', 
                        metavar = 'username:[password]',
                        required = True, 
                        help = 'set relay user and password')
    parser.add_argument('--tunnel', '-T', dest = 'tunnel', 
                        required = True,
                        help = 'tunnel id for data transmission')    
    parser.add_argument('--version', action='version', version='0.1')
    args = parser.parse_args()

    return args

class ClientAgent(BaseAgent):
    def __init__(self, config):
        BaseAgent.__init__(self, config, 'client')

        self._tunnel = self._config.tunnel

    def start(self):
        self.listen(self._config.port)
        self._log.info("listen port %d" % (self._config.port))

        self._checkTunnel()

    def handle_stream(self, stream, address):
        self._log.info('handle stream %s' % str(address))

        if self._stream and not self._stream.closed():
            self._log.error('handle stream, conflict')
            stream.close()
            return

        self._stream = stream

        self.sendRelayData(action = AgentAction.Connect, data = '')

        def onStreaming(data):
            self._log.info('client recv data %d' % len(data))

            self.sendRelayData(action = AgentAction.Stream, data = data)

            self._stream.read_bytes(MAX_READ_BYTES, None, onStreaming)

        def onClose():
            self._log.error('client was closed')
            self.sendRelayData(action = AgentAction.Error, 
                               data = 'connectionClosed')

        self._stream.set_close_callback(onClose)

        self._stream.read_bytes(MAX_READ_BYTES, None, onStreaming)

    def _checkTunnel(self):
        request = self.buildRequest('/tunnel')

        def callback(response):
            if response.error:
                self._log.error('checkTunnel Error %s, exit!' % response.error)
                sys.exit(2)
            else:
                self._log.warning('checkTunnel ok')

        self._client.fetch(request, callback)


    def handleRecvData(self, data):
        self._log.info('handleRecvData %d' % len(data))

        if self._stream.closed():
            self._log.warning('stream is closed')
            return

        self._stream.write(data)

    def handleRecvError(self, data):
        self._log.error('remote agent error %s, close stream too!' % (data))
        if not self._stream.closed():
            self._stream.set_close_callback(None)
            self._stream.close()

def main():
    app = ClientAgent(parseArgs())
    app.start()

    IOLoop.instance().start()

if __name__ == '__main__':
    main()
