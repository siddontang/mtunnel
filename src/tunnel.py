#coding=utf8
#siddontang@gmail.com

import time

from collections import deque

from misc import Singleton

ChannelKeepAlive = 600

class Buffer:
    def __init__(self, tunnel):
        self._buf = deque()
        self._callback = None
        self._tunnel = tunnel

    def save(self, data):
        if self._callback:
            self._callback(data)
        else:
            self._buf.append(data)

    def pop(self):
        try:
            return self._buf.popleft()
        except:
            return None

    def setCallback(self, callback):
        self._callback = callback

class Tunnel:
    def __init__(self, now):
        self._expiredTime = now + ChannelKeepAlive

        self._clientBuffer = Buffer(self)
        self._remoteBuffer = Buffer(self)

    def update(self):
        self._expiredTime = int(time.time()) + ChannelKeepAlive

    def timeout(self, expTime):
        return self._expiredTime < expTime

    def getClientBuffer(self):
        return self._clientBuffer

    def getRemoteBuffer(self):
        return self._remoteBuffer


class TunnelMgr(Singleton):
    def init(self):
        self._baseId = int(time.time() * 1000)
        self._tunnels = {}

    def generate(self):
        tid = int(time.time() * 1000)
        
        while (tid in self._tunnels):
            time.sleep(0.05)
            tid = int(time.time() * 1000)

        self._tunnels[tid] = Tunnel(tid / 1000)

        return tid

    def get(self, tid):
        return self._tunnels.get(tid)

    def update(self, tid):
        tunnel = self._tunnels.get(tid)
        if not tunnel:
            return

        tunnel.update()

    def check(self):
        expired = int(time.time())

        tids = [ tid for tid, tunnel in self._tunnels.iteritems() 
                if tunnel.timeout(expired)]

        [ self._tunnels.pop(tid, None) for tid in tids ]

        return tids
