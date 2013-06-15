#coding=utf8
#siddontang@gmail.com

import argparse
import time

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPRequest

try:
    from tornado.tcpserver import TCPServer
except:
    from tornado.netutil import TCPServer

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

def checkChannel(env):
    config = env.config
    client = env.client

    url = '%s://%s/channel?cid=%d' % (config.protocol, config.server, config.channel)
    
    def callback(response):
        if response.error:
            print 'channel id %d is invalid, exit!' % (config.channel)
            IOLoop.instance().stop()

    client.fetch(url, callback)

class ForwardProxy(TCPServer):
    def __init__(self, env):
        self._env = env
        self._client = env.client
        config = env.config

        self._cid = config.channel
        self._url = '%s://%s' % (config.protocol, config.server)

        TCPServer.__init__(self)

    def handle_stream(self, stream, address):
        def streamingCallback(data):
            print 'streamingCallback data len: %d' % (len(data))

            if len(data) > 0:
                self._sendForwardData(stream, data)

            stream.read_bytes(1024, None, streamingCallback)

        def closeCallback():
            print 'connection was closed, exit!'
            IOLoop.instance().stop()            

        stream.set_close_callback(closeCallback)
        stream.read_bytes(1024, None, streamingCallback)

    def _sendForwardData(self, stream, data):
        url = '%s/forwardproxy?cid=%d' % (self._url, self._cid)

        request = HTTPRequest(url, method = 'POST', body = data)

        def callback(response):
            if response.error:
                print 'forward data error %s, exit!' % response.error
                IOLoop.instance().stop()
            else:
                self._recvReverseData(stream)

        self._client.fetch(request, callback)

    def _recvReverseData(self, stream):
        url = '%s/reverseproxy?cid=%d' % (self._url, self._cid)

        request = HTTPRequest(url, request_timeout = 300)

        def callback(response):
            if response.error:
                print 'recv data error %s, exit!' % response.error
            else:
                if response.body:
                    stream.write(response.body)
                else:
                    def _callback():
                        self._recvReverseData(stream)

                    IOLoop.instance().add_timeout(time.time() + 1, _callback)


        self._client.fetch(request, callback)        

class Object:
    pass

def main():
    env = Object()
    env.client = AsyncHTTPClient()

    args = parseArgs()

    env.config = args

    port = args.port

    server = args.server

    print 'start listen port %d' % port

    print 'server address %s' % server

    application = ForwardProxy(env)
    application.listen(port)

    checkChannel(env)

    IOLoop.instance().start()

if __name__ == '__main__':
    main()