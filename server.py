#coding=utf8
#siddontang@gmail.com

import tornado.ioloop
import tornado.web

import argparse
import time
from channel import ChannelMgr

class ChannelHandler(tornado.web.RequestHandler):
    def post(self):
        cid = ChannelMgr().genId()

        self.write(str(cid))
        self.finish()

    def get(self):
        cid = int(self.get_argument('cid'))
        channel = ChannelMgr().get(cid)
        if not channel:
            self.send_error(410)
        else:
            self.finish()

class BaseProxyHandler(tornado.web.RequestHandler):
    def checkChannel(self):
        cid = int(self.get_argument('cid'))
        channel = ChannelMgr().get(cid)
        if not channel:
            self.send_error(410)
            return None

        return channel

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

class ForwardProxyHandler(BaseProxyHandler):
    @tornado.web.asynchronous   
    def get(self):
        channel = self.checkChannel()
        if not channel:
            return

        self._get(channel.getFBuf())

    def post(self):
        channel = self.checkChannel()
        if not channel:
            return

        self._post(channel.getFBuf())

class ReverseProxyHandler(BaseProxyHandler):
    @tornado.web.asynchronous   
    def get(self):
        channel = self.checkChannel()
        if not channel:
            return

        self._get(channel.getRBuf())

    def post(self):
        channel = self.checkChannel()
        if not channel:
            return

        self._post(channel.getRBuf())

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

    ChannelMgr().init()

    print 'begin to listen port %d' % (port)

    application = tornado.web.Application([
        (r'/forwardflow', ForwardProxyHandler),
        (r'/reverseflow', ReverseProxyHandler),
        (r'/channel', ChannelHandler),
    ])

    application.listen(port)

    def onChannelCheck():
        ChannelMgr().check()
        tornado.ioloop.IOLoop.instance().add_timeout(int(time.time()) + 30, onChannelCheck)

    tornado.ioloop.IOLoop.instance().add_timeout(int(time.time()) + 30, onChannelCheck)

    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()