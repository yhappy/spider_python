#! /usr/bin/env python
#coding=utf-8
'''
#=============================================================================
#     FileName: webserver.py
#         Desc: 一个简易的web服务器。运行程序之后，请不要关闭运行窗口，可以在浏览器中通过地址 “http://127.0.0.1:9000/” 访问爬虫找到的工作链接。
#       Author: mmoonzhu
#        Email: myzhu@tju.edu.cn
#     HomePage:
#      Version: 0.0.1
#   LastChange: 2013-08-12 14:00:00
#      History:
#=============================================================================
'''

import redis
import BaseHTTPServer


HOST_NAME = '127.0.0.1' # !!!REMEMBER TO CHANGE THIS!!!
PORT_NUMBER = 8082 # Maybe set this to 9000.


class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        s.wfile.write(page())


def page():
    string = ''
    string += '''
    <html>
    <head>
    <title>Welcome to spider!</title>
    <style>
        body {
            width: 35em;
            margin: 0 auto;
        }
        a:visited { color: red; }
    </style>
    </head>
    <body>
    <br/>
    '''
    r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
    info = r.info()
    ret = r.smembers('urls')
    for herf in ret:
        s = herf.decode('u8').encode('gbk')
        string += s + "<br/>"
    string += '</body>'
    string += '</html>'
    return string


if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
