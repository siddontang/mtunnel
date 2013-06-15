#coding=utf8
#siddontang@gmail.com

import argparse
import socket
import time
import sys

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPRequest

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


def requestChannel(env):
    config = env.config
    client = env.client

    url = '%s://%s/channel' % (config.protocol, config.server)
    
    def callback(response):
        if response.error:
            print 'requestChannel error %s, exit!' % (response.error)
            sys.exit(2)
        else:
            cid = int(response.body)
            env.cid = cid
            print 'channel id is %d' % (cid)

        IOLoop.instance().stop()

    request = HTTPRequest(url, method = 'POST', body = '')
    client.fetch(request, callback)

    IOLoop.instance().start()


class ReverseProxy:
    def __init__(self, env):
        self._env = env
        self._client = env.client
        config = env.config
        self._cid = env.cid

        self._url = '%s://%s' % (config.protocol, config.server)

    def connect(self):
        host = self._env.config.host
        port = self._env.config.port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = IOStream(s)

        def callback():
            print 'connect ok, begin to recv forward data'
            self._recvForwardData(stream)

        def closeCallback():
            print 'connection was closed, exit!'
            IOLoop.instance().stop()            

        stream.connect((host, port), callback)

    def _recvForwardData(self, stream):
        url = '%s/forwardproxy?cid=%d' % (self._url, self._cid)

        request = HTTPRequest(url, request_timeout = 300)

        def callback(response):
            if response.error:
                print 'recv forward data error %s, exit!' % (response.error)
                IOLoop.instance().stop()
            else:
                if response.body:
                    stream.write(response.body)

                    self._recvData(stream)
                else:
                    def _callback():
                        self._recvForwardData(stream)

                    IOLoop.instance().add_timeout(time.time() + 1, _callback)


        self._client.fetch(request, callback)

    def _sendReverseData(self, stream, data):
        url = '%s/reverseproxy?cid=%d' % (self._url, self._cid)

        request = HTTPRequest(url, method = 'POST', body = data)

        def callback(response):
            if response.error:
                print 'forward data error %s, exit!' % response.error
                IOLoop.instance().stop()
            else:
                self._recvForwardData(stream)

        self._client.fetch(request, callback)

    def _recvData(self, stream):
        def streamingCallback(data):
            print 'streamingCallback data len: %d' % (len(data))

            if len(data) > 0:
                self._sendReverseData(stream, data)

            stream.read_bytes(1024, None, streamingCallback)

        stream.read_bytes(1024, None, streamingCallback)

class Object:
    pass

def main():
    env = Object()
    env.client = AsyncHTTPClient()

    args = parseArgs()

    env.config = args

    host = args.host
    port = args.port

    server = args.server

    print 'start connect host:port = %s:%d' % (host, port)

    print 'server address %s' % server

    requestChannel(env)

    application = ReverseProxy(env)
    application.connect()

    IOLoop.instance().start()

if __name__ == '__main__':
    main()