#coding=utf8
#siddontang@gmail.com

import time
import hmac
import hashlib

from misc import Singleton

class Auth(Singleton):
    def __init__(self):
        pass

    def loadAuth(self):
        self._auths = {
            'test' : '123'
        }

    def checkAuth(self, auth):
        auth = auth.decode('base64')
        username, t, digest = auth.split(':')
        t = int(t)
        password = str(self._auths.get(username))
        if not password:
            return 'userNotExists'

        h = hmac.new(hashlib.md5(password).digest(), 
                    'mtunnel:%s:%d' % (username, t), hashlib.sha1)

        if h.digest().encode('base64').replace('\n', '') == digest:
            return 'ok'
        else:
            return 'invalidPassowrd'