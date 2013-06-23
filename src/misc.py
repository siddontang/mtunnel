#coding=utf8
#siddontang@gmail.com

import socket
import struct
import logging


def ip2Int(ip):
    return struct.unpack("!I",socket.inet_aton(ip))[0]

def int2Ip(i):
    return socket.inet_ntoa(struct.pack("!I",i))


class AgentAction:
    Connect = 0
    Stream  = 1
    Error   = 2

def getLogger(level = logging.INFO):
    mtunnelLog = logging.getLogger("mtunnel")

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter('%(asctime)-15s %(levelname)-5s %(message)s')
    ch.setFormatter(formatter)
    mtunnelLog.addHandler(ch)

    return mtunnelLog

class Singleton(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance
