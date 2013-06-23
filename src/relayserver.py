#coding=utf8
#siddontang@gmail.com

import tornado.ioloop
import tornado.web

import argparse
import time
from tunnel import TunnelMgr
from auth import Auth

from tornado.ioloop import IOLoop
from tornado.web import asynchronous, RequestHandler, HTTPError

class BaseHandler(RequestHandler):
    def prepare(self):
        self.checkAuth()
        self.checkTunnel()

    def checkAuth(self):
        auth = self.request.headers['MT-Authorization']
        hr = Auth().checkAuth(auth)
        if hr != 'ok':
            raise HTTPError(510, str(hr))

    def checkTunnel(self):
        tunnelId = int(self.get_argument('tunnel'))
        tunnel = TunnelMgr().get(tunnelId)
        if not tunnel:
            raise HTTPError(510, 'tunnelNotExists')

        self.tunnel = tunnel

class TunnelHandler(BaseHandler):
    def prepare(self):
        if self.request.method == 'POST':
            self.checkAuth()
        else:
            BaseHandler.prepare(self)

    def post(self):
        tunnelId = TunnelMgr().generate()

        self.write(str(tunnelId))
        self.finish()

    def get(self):
        self.finish()

    def put(self):
        self.tunnel.update()
        self.finish()

class AgentHandler(BaseHandler):
    def _post(self, buf):
        buf.save(self.request.body)
        self.finish()

    def _get(self, buf):
        hasData = False
        while True:
            data = buf.pop()
            if not data:
                break


            self.write(data)
            hasData = True

        if hasData:
            buf.setCallback(None)
            self.finish()
        else:
            def callback(data):
                buf.setCallback(None)
                self.write(data)
                self.finish()
    
            buf.setCallback(callback)


class ClientAgentHandler(AgentHandler):
    @asynchronous
    def get(self):
        clientBuffer = self.tunnel.getClientBuffer()
        self._get(clientBuffer)

    def post(self):
        remoteBuffer = self.tunnel.getRemoteBuffer()
        self._post(remoteBuffer)


class RemoteAgentHandler(AgentHandler):
    @asynchronous
    def get(self):
        remoteBuffer = self.tunnel.getRemoteBuffer()
        self._get(remoteBuffer)

    def post(self):
        clientBuffer = self.tunnel.getClientBuffer()
        self._post(clientBuffer)

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', dest = 'port',
                        metavar = 'N', type = int, default = 8888,
                        help = 'listen port. (default: 8888)')
    parser.add_argument('--version', action='version', version='0.1')
    args = parser.parse_args()

    return args

def main():
    args = parseArgs()
    port = args.port

    Auth().loadAuth()
    TunnelMgr().init()

    print 'begin to listen port %d' % (port)

    application = tornado.web.Application([
        (r'/tunnel', TunnelHandler),
        (r'/agent/client', ClientAgentHandler),
        (r'/agent/remote', RemoteAgentHandler),
    ])

    application.listen(port)

    def onTunnelCheck():
        TunnelMgr().check()
        IOLoop.instance().add_timeout(int(time.time()) + 30, onTunnelCheck)

    IOLoop.instance().add_timeout(int(time.time()) + 30, onTunnelCheck)

    IOLoop.instance().start()

if __name__ == '__main__':
    main()