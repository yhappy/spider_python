#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from BeautifulSoup import BeautifulSoup
from apscheduler.scheduler import Scheduler
from email.mime.text import MIMEText
from conf import *
from optparse import OptionParser

import smtplib
import sys
import email
import re
import redis
import requests


class HttpHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        crawler = Crawler()
        page = crawler.generate_page()
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(page)
        return


class Crawler:

    def __init__(self):
        self.rs = redis.Redis(host=REDIS_IP, port=REDIS_PORT)
        self.http_querys = (
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
                                {
									'host' : 'http://bbs.byr.cn',
									'url'  : 'http://bbs.byr.cn/board/Job',
                                    'headers' : {
                                        "X-Requested-With" : "XMLHttpRequest",
                                    },
                                    'href' : "^/article/Job/\d+$",
                                },
                        )

    def _parse_html_to_urls(self, host, url, headers, href):
        r = requests.get(url, headers=headers)
        r.encoding = 'GBK'
        frs_soup = BeautifulSoup(r.text)
        frs_attrs = {
            'href' : re.compile(href),
            'title' : None,
            'target' : None,
        }
        frs_res = frs_soup.findAll('a', frs_attrs)
        urls = []
        for res in frs_res:
            if res.parent.parent.get('class') != 'top':
                res['href'] = host + res['href']
                urls.append(res)
        return urls
    
    @staticmethod 
    def str_contains_any_tuple_elements(str, tup):
        if filter(lambda x: x in str, tup):
            return True
        return False

    def _put_web_url_into_redis(self, url):
        title = url.string
        if Crawler.str_contains_any_tuple_elements(title, WEB_FILETER_PRI_KEYS) or \
            Crawler.str_contains_any_tuple_elements(title, WEB_FILETER_KEYS) and \
            not Crawler.str_contains_any_tuple_elements(title, WEB_FILETER_EXCLUDE_KEYS):
                self.rs.sadd('web_urls', url)
    

    def _put_message_url_into_redis(self, url):
        if self.rs.sismember('outdated_message_urls', url):
            return
        title = url.string
        if Crawler.str_contains_any_tuple_elements(title, MESSAGE_FILETER_PRI_KEYS) or \
            Crawler.str_contains_any_tuple_elements(title, MESSAGE_FILETER_KEYS) and \
            not Crawler.str_contains_any_tuple_elements(title, MESSAGE_FILETER_EXCLUDE_KEYS):
                self.rs.sadd('current_message_urls', url)

    def _put_urls_into_redis(self, urls):
        for url in urls:
            self._put_web_url_into_redis(url)
            self._put_message_url_into_redis(url)

    def _delete_web_urls_if_needed(self):
        if int(self.rs.get('times')) >= REDIS_FLUSH_FREQUENCE:
            self.rs.delete('web_urls')
            self.rs.delete('times')

    def _get_message_urls_from_redis(self):
        ret = self.rs.smembers('current_message_urls')
        urls = ""
        for herf in ret:
            urls += herf + "<br>"
        return len(ret), urls

    def _get_web_urls_from_redis(self):
        ret = self.rs.smembers('web_urls')
        urls = ""
        for herf in ret:
            urls += "<tr><td>" + herf + "</td></tr>"
        return urls

    def _refresh_message_urls_in_redis(self):
        self.rs.sunionstore('outdated_message_urls', 'current_message_urls', 'outdated_message_urls')
        self.rs.delete('current_message_urls')

    def generate_page(self):
        return '''
                <html>
                    <head>
                        <meta charset="utf-8">
                        <title>Welcome to spider!</title>
                        <link href="//cdnjs.bootcss.com/ajax/libs/twitter-bootstrap/2.3.1/css/bootstrap.min.css" rel="stylesheet">
                        <style>
                            body {
                                width: 35em;
                                margin: 0 auto;
                            }
                            .table-hover tbody tr:hover > td,
                                .table-hover tbody tr:hover > th {
                                background-color: #D2DAFF;
                            }
                            a:visited { color: red; }
                        </style>
                    </head>
                    <body>
                        <h3>招聘信息筛选</h3>
                        <h4 class="text-info">红色链接为您已打开过的链接</h4><hr>
                        <div class="well well-large">
                            <table class="table table-hover">
                                <tbody>
                                    %s
                                </tbody>
                            </table>
                    </body>
                    </html>
                ''' % self._get_web_urls_from_redis()

    def send_massage(self, *args, **kwargs):
        msg_num, content = self._get_message_urls_from_redis()
        if msg_num <= 0 :
            print "none messages to send..."
            return
        sub = "抓取到%d条高优先级校招信息" % msg_num
        send_mail_address = SEND_MAIL_USER_NAME + "<" + SEND_MAIL_USER + "@" + SEND_MAIL_POSTFIX + ">"
        msg = MIMEText(content, 'html', 'utf-8')
        msg["Accept-Language"]="zh-CN"
        msg["Accept-Charset"]="ISO-8859-1, utf-8"
        msg['Subject'] = sub
        msg['From'] = send_mail_address
        try:
            stp = smtplib.SMTP()
            stp.connect(SEND_MAIL_HOST)
			# NOTE(xiyoulaoyuanjia): it get error do not have
			# it smtplib.SMTPException: SMTP AUTH extension not supported by server
            stp.starttls()
            stp.login(SEND_MAIL_USER, SEND_MAIL_PASSWORD)
			# FIX(xiyoulaoyuanjia): here if sms get error. do not
			# send email notification
            if kwargs['sms']:
                msg['to'] = to_adress = "139SMSserver<" + RECEIVE_MAIL_USER_139 + "@" + RECEIVE_MAIL_POSTFIX_139 + ">"
                stp.sendmail(send_mail_address, to_adress, msg.as_string())
            if kwargs['email']:
                msg['to'] = to_adress = RECEIVE_MAIL_USER + "@" + RECEIVE_MAIL_POSTFIX
                stp.sendmail(send_mail_address, to_adress, msg.as_string())
            print "send message sucessfully..."
            self._refresh_message_urls_in_redis()
        except Exception, e:
            print "fail to send message: "+ str(e)
        finally:
            stp.close()

    def run(self):
        print "start crawler ..."
        self.rs.incr('times')
        self._delete_web_urls_if_needed()
        for http_query in self.http_querys :
            urls = self._parse_html_to_urls(http_query['host'], http_query['url'], http_query['headers'], http_query['href'])
            self._put_urls_into_redis(urls)
        print "finish crawler ..."


if __name__ == '__main__':

    parser = OptionParser(description='a crawer which get jobs info.')
    parser.add_option('-s', '--sms', dest='sms', action='store_true',
			            help='send sms mode')
    parser.add_option('-e', '--email', dest='email', action='store_true',
			            help='send email mode')
    (options, args) = parser.parse_args(args=sys.argv[1:])
    crawler = Crawler()
    crawler.run()

    sched = Scheduler()
    sched.start()
    sched.add_interval_job(crawler.run, hours=CRAWLER_FREQUENCE_HOURS)
    sched.add_interval_job(crawler.send_massage, minutes=MESSAGE_FREQUENCE_MINUTES, kwargs=options.__dict__)


    try:
        print "start server ..."
        server = HTTPServer((HOST_NAME, PORT_NUMBER), HttpHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print "finish server ..."
        server.socket.close()
