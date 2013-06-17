#coding=utf8
#siddontang@gmail.com

import argparse
import socket
import time
import sys

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.httpclient import AsyncHTTPClient, HTTPClient
from tornado.httpclient import HTTPRequest

from misc import ActionType

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-host', dest = 'host',
                        metavar = 'Host', required = True,
                        help = 'endpoint host, like sshd server ip')
    parser.add_argument('--port', '-p', dest = 'port',
                        metavar = 'Port', type = int, required = True,
                        help = 'endpoint port, like sshd server port')
    parser.add_argument('--server', dest = 'server',
                        metavar = 'Host:Port', required = True,
                        help = 'server address to connect')
    parser.add_argument('--protocol', dest = 'protocol',
                        default = 'http',
                        help = 'http protocol (default: http)')
    parser.add_argument('--version', action='version', version='0.1')
    args = parser.parse_args()

    return args

class ReverseProxy:
    def __init__(self, env):
        self._env = env
        self._client = AsyncHTTPClient()
        self._syncClient = HTTPClient()

        config = env.config

        self._url = '%s://%s' % (config.protocol, config.server)

    def requestChannel(self):
        url = '%s/channel' % (self._url)
        request = HTTPRequest(url, method = 'POST', body = '')
        response = self._syncClient.fetch(request)

        if response.error:
            print 'requestChannel error %s, exit!' % (response.error)
            sys.exit(2)
        else:
            cid = int(response.body)
            self._cid = cid
            print 'channel id is %d' % (cid)

    def start(self):
        self._recvFromRelay(None)

    def _connect(self):
        host = self._env.config.host
        port = self._env.config.port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = IOStream(s)

        def callback():
            print 'connect ok, begin to recv data'
            self._recvData(stream)

            self._recvFromRelay(stream)

        def closeCallback():
            print 'connection was closed!'

        stream.set_close_callback(closeCallback)
        stream.connect((host, port), callback)

    def _sendToRelay(self, stream, actionType, data):
        url = '%s/reverseflow?cid=%d' % (self._url, self._cid)

        body = '%04d%1d%s' % (len(data), actionType, data)
        request = HTTPRequest(url, method = 'POST', body = body)

        def callback(response):
            if response.error:
                print 'forward data error %s, exit!' % response.error
                IOLoop.instance().stop()
            else:
                self._recvFromRelay(stream)

        self._client.fetch(request, callback)

    def _recvFromRelay(self, stream):
        url = '%s/forwardflow?cid=%d' % (self._url, self._cid)

        request = HTTPRequest(url, request_timeout = 1800)

        def callback(response):
            if response.error:
                print 'recv forward data error %s, exit!' % (response.error)
                IOLoop.instance().stop()
                sys.exit(2)
            else:
                body = response.body
                while body:
                    length = int(body[0:4])
                    actionType = int(body[4])
                    if actionType == ActionType.Connect:
                        self._connect()
                    elif actionType == ActionType.Data:
                        data = body[5:5 + length]
                        stream.write(data)
                        self._recvData(stream)
                        self._recvFromRelay(stream)
                    elif actionType == ActionType.Error:
                        print 'some error occur, exit!'
                        sys.exit(2)

                    body = body[5 + length:]

        self._client.fetch(request, callback)

    def _recvData(self, stream):
        def streamingCallback(data):
            print 'streamingCallback data len: %d' % (len(data))

            if len(data) > 0:
                self._sendToRelay(stream, ActionType.Data, data)

            stream.read_bytes(1024, None, streamingCallback)

        stream.read_bytes(1024, None, streamingCallback)

class Object:
    pass

def main():
    env = Object()

    args = parseArgs()

    env.config = args

    host = args.host
    port = args.port

    server = args.server

    print 'start connect host:port = %s:%d' % (host, port)

    print 'server address %s' % server

    application = ReverseProxy(env)
    application.requestChannel()

    application.start()

    IOLoop.instance().start()

if __name__ == '__main__':
    main()