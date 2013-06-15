#coding=utf8
#siddontang@gmail.com

import tornado.ioloop
import tornado.web

import argparse

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

class ForwardProxyHandler(BaseProxyHandler):
    @tornado.web.asynchronous   
    def get(self):
        channel = self.checkChannel()
        if not channel:
            return

        while True:
            buf = channel.popFBuf()
            if not buf:
                break
                
            self.write(buf)

        self.finish()

    def post(self):
        channel = self.checkChannel()
        if not channel:
            return

        channel.saveFBuf(self.request.body)
        self.finish()

class ReverseProxyHandler(BaseProxyHandler):
    @tornado.web.asynchronous   
    def get(self):
        channel = self.checkChannel()
        if not channel:
            return

        while True:
            buf = channel.popRBuf()
            if not buf:
                break

            self.write(buf)

        self.finish()

    def post(self):
        channel = self.checkChannel()
        if not channel:
            return

        channel.saveRBuf(self.request.body)
        self.finish()

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
        (r'/forwardproxy', ForwardProxyHandler),
        (r'/reverseproxy', ReverseProxyHandler),
        (r'/channel', ChannelHandler),
    ])

    application.listen(port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()