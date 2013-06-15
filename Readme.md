# Introduction

# Usage

## start server

        python server.py

## start reverse proxy

        python rproxy.py -host 127.0.0.1 -p 80 --server 127.0.0.1:8888

    it will return a channel id, use this channel id in forword proxy.

## start forward proxy

        python fproxy.py --server 127.0.0.1:8888 --channel 0

