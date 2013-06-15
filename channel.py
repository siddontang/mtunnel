#coding=utf8
#siddontang@gmail.com

from singleton import Singleton 
from collections import deque

import time

ChannelKeepAlive = 300

class Channel:
    def __init__(self, now):
        self._expiredTime = now + ChannelKeepAlive

        self._fbuf = deque()
        self._rbuf = deque()

    def update(self):
        self._expiredTime = int(time.time()) + ChannelKeepAlive

    def timeout(self, expTime):
        return self._expiredTime < expTime

    def saveFBuf(self, data):
        self._fbuf.append(data)

        self.update()

    def saveRBuf(self, data):
        self._rbuf.append(data)

        self.update()

    def popFBuf(self):
        self.update()

        try:
            return self._fbuf.popleft()
        except:
            return None

    def popRBuf(self):
        self.update()

        try:
            return self._rbuf.popleft()
        except:
            return None

    def save(self, data, queue):
        queue.append(data)

        self.update()

    def pop(self, queue):
        self.update()

        try:
            return queue.popleft()
        except:
            return None

    def getFBuf(self):
        return self._fbuf

    def getRBuf(self):
        return self._rbuf

class ChannelMgr(Singleton):
    def init(self):
        self._baseId = int(time.time() * 1000)
        self._channels = {}

    def genId(self):
        cid = int(time.time() * 1000)
        
        while (cid in self._channels):
            time.sleep(0.05)
            cid = int(time.time() * 1000)

        self._channels[cid] = Channel(cid / 1000)

        return cid

    def get(self, cid):
        return self._channels.get(cid)

    def update(self, cid):
        channel = self._channels.get(cid)
        if not channel:
            return

        channel.update()

    def check(self):
        '''
            check expired channel which has no data exchanged for a long time.
            Then remove these expired channels.
        '''
        expired = int(time.time())

        cids = [ cid for cid, channel in self._channels.iteritems() 
                if channel.timeout(expired)]

        [ self._channels.pop(cid, None) for cid in cids ]

        return cids

if __name__ == '__main__':
    ChannelMgr().init()
    cid = ChannelMgr().genId()
    
    channel = ChannelMgr().get(cid)

    channel.saveRBuf('123')
    channel.saveRBuf('456')

    print channel.popRBuf()
    print channel.popRBuf()
    print channel.popRBuf()

    channel.saveFBuf('123')
    channel.saveFBuf('456')

    print channel.popFBuf()
    print channel.popFBuf()
    print channel.popFBuf()
