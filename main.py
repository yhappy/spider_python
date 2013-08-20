#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
#=============================================================================
#     FileName: main.py
#         Desc: 运行程序之后，请不要关闭运行窗口，可以在浏览器中通过"http://127.0.0.1:8888"访问爬虫找到的工作链接。
#       Author: lizherui, mmoonzhu
#        Email: lzrak47m4a1@gmail.com, myzhu@tju.edu.cn
#     HomePage: https://github.com/lizherui/spider_python
#      Version: 0.0.1
#   LastChange: 2013-08-20 15:27:25
#=============================================================================
'''

import redis
import re
import requests
import logging
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from BeautifulSoup import BeautifulSoup

LOG_ADDRESS = '/usr/local/var/log/spider_logging.txt'                   # 日志文件地址
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'     # 日志格式
LOG_LEVEL = logging.DEBUG                                               # 日志级别
HOST_NAME = '127.0.0.1'                                                 # Web页面的ip
PORT_NUMBER = 8888                                                      # Web页面的port
REDIS_IP = '127.0.0.1'                                                  # Redis的ip
REDIS_PORT = 6379                                                       # Redis的port
REDIS_FREQUENCE = 10                                               # Redis清空的频率
SPIDER_KEYS = (u'校招', u'应届', u'毕业生', 'Google')                   # 筛选的关键词


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Respond to a GET request."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        crawler = Crawler()
        page = crawler.run()
        self.wfile.write(page)
        return 
    

class Crawler:

    def __init__(self):
        self.logger = self._init_log()
        self.rs = redis.Redis(host=REDIS_IP, port=REDIS_PORT)
        self.http_querys = self._init_http_querys()

    def _init_log(self):
        logger = logging.getLogger() 
        handler = logging.FileHandler(LOG_ADDRESS)
        formatter = logging.Formatter(LOG_FORMAT) 
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(LOG_LEVEL)
        logger.info('Crawler start!')
        return logger

    def _init_http_querys(self):
        return (
                {
                    'host' : 'http://bbs.byr.cn',
                    'url'  : 'http://bbs.byr.cn/board/JobInfo',
                    'headers' : {
                        "X-Requested-With" : "XMLHttpRequest",
                    },
                    'href' : "^/article/JobInfo/\d+$",
                },

                {
                    'host' : 'http://www.newsmth.net',
                    'url'  : 'http://www.newsmth.net/nForum/board/Career_Campus',
                    'headers' : {
                        "X-Requested-With" : "XMLHttpRequest",
                    },
                    'href' : "^/nForum/article/Career_Campus/\d+$",
                },
            )

    def _parse_html_to_urls(self, host, url, headers, href):
        r = requests.get(url, headers = headers)
        frs_soup = BeautifulSoup(r.text)
        frs_attrs = {
            'href' : re.compile(href),
            'title' : None,
            'target' : None,
        }
        frs_res =  frs_soup.findAll('a', frs_attrs)
        urls = []
        for res in frs_res:
            if res.parent.parent.get('class') != 'top':
                res['href'] = host + res['href']
                urls.append(res)
        return urls

    def _put_urls_into_redis(self, urls, rs):
        for url in urls:
            title = url.string
            if filter(lambda x: x in title, SPIDER_KEYS):
                rs.sadd('urls', url)

    def _flush_redis_at_times(self, rs):
        rs.incr('times')
        if int(rs.get('times')) >= REDIS_FREQUENCE:
            rs.flushall()

    def _crawl_html(self, rs, host, url, headers, href):
        urls = self._parse_html_to_urls(host, url, headers, href)
        self._put_urls_into_redis(urls, rs)

    def _get_urls_from_redis(self):
        ret = self.rs.smembers('urls')
        urls = "" 
        for herf in ret:
            urls += herf + "<br/>"
        return urls

    def _generate_page(self):
        return '''
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
                        %s
                    </body>
                    </html>
                ''' % self._get_urls_from_redis()

    def run(self):
        self._flush_redis_at_times(self.rs)
        for http_query in self.http_querys :
            self._crawl_html(self.rs, http_query['host'], http_query['url'], http_query['headers'], http_query['href'])
        return self._generate_page()

    def __del__(self):
        self.logger.info("Crawler finish!\n") 

if __name__ == '__main__':
    try:
        server = HTTPServer((HOST_NAME, PORT_NUMBER), HttpHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        server.socket.close()
