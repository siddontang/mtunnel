#coding=utf8
#siddontang@gmail.com

import hashlib
import hmac
import urllib
import time

from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient, HTTPClient
from tornado.httpclient import HTTPRequest
        
try:
    from tornado.tcpserver import TCPServer
except:
    from tornado.netutil import TCPServer

from misc import getLogger
from misc import AgentAction

class BaseAgent(TCPServer):
    def __init__(self, config, agentType):
        self._config = config
        self._log = getLogger()
        self._client = AsyncHTTPClient()
        self._syncClient = HTTPClient()

        self._agentType = agentType 
        self._parseConfig()

        self._tunnel = 0
        self._hangUp = False

        self._stream = None

        TCPServer.__init__(self)

    def sendRelayData(self, action, data):
        self._log.warning('%s sendRelayData %d %d' % (self._agentType, action, len(data)))

        body = '%1d%04d%s' % (action, len(data), data)
        request = self.buildRequest('/agent/%s' % self._agentType, method = 'POST', 
                                    body = body)

        response = self._syncClient.fetch(request)
        if response.error:
            self._log.error('%s sendRelayData Error %s' % (self._agentType, response.error))
        else:
            self._log.error('%s sendRelayData ok, now to recv!' % (self._agentType))

            self.recvRelayData()


    def recvRelayData(self):
        if self._hangUp:
            self._log.warning('recvConnection has already hang up!')
            return

        self._hangUp = True

        def callback(response):
            self._hangUp = False
            if response.error:
                self._log.error('%s recvRelayData Error %s' % (self._agentType, response.error))
            else:
                self._log.warning('%s recvRelayData ok, %d' % (self._agentType, len(response.body)))

                body = response.body

                while body:
                    actionType = int(body[0])
                    length = int(body[1:5])
                    data = body[5:5 + length]

                    if actionType == AgentAction.Stream:
                        self.handleRecvData(data)
                    elif actionType == AgentAction.Error:
                        self.handleRecvError(data)
                    elif actionType == AgentAction.Connect:
                        self.handleRecvConnect(data)

                    body = body[5 + length:]

                self.recvRelayData()

        request = self.buildRequest('/agent/%s' % (self._agentType))

        self._client.fetch(request, callback)

    def handleRecvData(self, data):
        raise NotImplementedError

    def handleRecvError(self, data):
        raise NotImplementedError

    def handleRecvConnect(self, data):
        raise NotImplementedError

    def _parseConfig(self):
        username, password = self._config.user.split(':')

        self._relayUrl = 'http://%s' % (self._config.relay)

        self._username = username
        self._password = password

    def buildAuth(self):    
        t = int(time.time())
        h = hmac.new(hashlib.md5(self._password).digest(), 
                    'mtunnel:%s:%d' % (self._username, t), hashlib.sha1)

        auth = ('%s:%d:%s' % (self._username, t, h.digest().encode('base64').replace('\n', '')))

        return auth.encode('base64').replace('\n', '')

    def buildRequest(self, uri, method = 'GET', body = None, 
                    params = {}, headers = {}):

        params['tunnel'] = self._tunnel
        args = urllib.urlencode(params)
        args = '?%s' % args if args else ''

        url = '%s%s%s' % (self._relayUrl, uri, args) 

        headers['MT-Authorization'] = self.buildAuth()

        request_timeout = 3600 if method == 'GET' else 20

        request = HTTPRequest(url, method = method, body = body, 
                              headers = headers, request_timeout = request_timeout)
        return request


