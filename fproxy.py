#coding=utf8
#siddontang@gmail.com

import argparse
import time
import sys

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient, HTTPClient
from tornado.httpclient import HTTPRequest
        
try:
    from tornado.tcpserver import TCPServer
except:
    from tornado.netutil import TCPServer

from misc import ActionType

MAX_READ_BYTES = 1024 * 1024

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', dest = 'channel',
                        metavar = 'N', type = int, required = True,
                        help = 'channel id')
    parser.add_argument('--port', '-p', dest = 'port',
                        metavar = 'N', type = int, default = 8889,
                        help = 'listen port. (default: 8889)')
    parser.add_argument('--server', dest = 'server',
                        metavar = 'Host:Port', required = True,
                        help = 'server address to connect')
    parser.add_argument('--protocol', dest = 'protocol',
                        default = 'http',
                        help = 'http protocol (default: http)')
    parser.add_argument('--version', action='version', version='0.1')
    args = parser.parse_args()

    return args

class ForwardProxy(TCPServer):
    def __init__(self, env):
        self._env = env
        
        self._client = AsyncHTTPClient()

        self._syncClient = HTTPClient()


        config = env.config

        self._cid = config.channel
        self._url = '%s://%s' % (config.protocol, config.server)

        self._hangUp = False

        TCPServer.__init__(self)

    def checkChannel(self):
        url = '%s/channel?cid=%d' % (self._url, self._cid)
        
        response = self._syncClient.fetch(url)

        if response.error:
            print 'channel id %d is invalid, exit!' % (self._cid)
            sys.exit(2)

    def handle_stream(self, stream, address):
        self._sendToRelay(stream, ActionType.Connect, '')

        def callback(data):
            print 'callback data len: %d' % (len(data))

            if len(data) > 0:
                self._sendToRelay(stream, ActionType.Data, data)

            stream.read_bytes(MAX_READ_BYTES, None, callback)

        def closeCallback():
            print 'connection was closed!'

        stream.set_close_callback(closeCallback)
        stream.read_bytes(MAX_READ_BYTES, None, callback)

    def _sendToRelay(self, stream, actionType, data):
        url = '%s/forwardflow?cid=%d' % (self._url, self._cid)
        print 'sendToRelay', actionType, len(data)
        
        body = '%04d%1d%s' % (len(data), actionType, data)
        request = HTTPRequest(url, method = 'POST', body = body)

        def callback(response):
            if response.error:
                print 'send to relay error %s, exit!' % response.error
                IOLoop.instance().stop()
            else:
                self._recvFromRelay(stream)

        self._client.fetch(request, callback)


    def _recvFromRelay(self, stream):
        if self._hangUp:
            return

        self._hangUp = True

        url = '%s/reverseflow?cid=%d' % (self._url, self._cid)
        
        request = HTTPRequest(url, request_timeout = 3600)

        def callback(response):
            self._hangUp = False
            if response.error:
                print 'recv from relay error %s!' % response.error
            else:
                body = response.body
                while body:
                    length = int(body[0:4])
                    actionType = int(body[4])
                    if actionType == ActionType.Data:
                        data = body[5:5 + length]
                        stream.write(data)
                    elif actionType == ActionType.Error:
                        print 'some error occur, exit!'
                        sys.exit(2)

                    body = body[5 + length:]

                self._recvFromRelay(stream)

        self._client.fetch(request, callback)        


class Object:
    pass

def main():
    env = Object()

    args = parseArgs()

    env.config = args

    port = args.port

    server = args.server

    print 'start listen port %d' % port

    print 'server address %s' % server

    application = ForwardProxy(env)

    application.checkChannel()
    
    application.listen(port)

    IOLoop.instance().start()

if __name__ == '__main__':
    main()