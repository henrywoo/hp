#!/usr/bin/env python
from tornado.options import options, define, parse_command_line
from django.utils.timezone import utc
from tornado import httpserver, ioloop, web, wsgi
import django.core.handlers.wsgi
import colored_traceback.always
import os, sys
import datetime   
import json
import logging
from tornado import websocket
import subprocess

######################################################################
PROJNAME = 'mysite'
define('port', type=int, default=8888)
######################################################################
CMD=['/bin/bash','/root/fuheng/tornado-django/r.sh']
MSG=[]

_HERE = os.path.dirname(os.path.abspath(__file__))
print _HERE
sys.path.append(_HERE)
os.environ['DJANGO_SETTINGS_MODULE'] = PROJNAME + '.settings'
os.environ['PYTHONPATH'] = '.'
print django.VERSION
django.setup()

class CommandHandler(web.RequestHandler):
    def get(self):
        self.render("command.html")

class HelloHandler(web.RequestHandler):
  def get(self):
    self.write('Hello from tornado')
    self.write(''.join(MSG))

def jsondata(s):
    data = {"msg": s}
    return json.dumps(data)

observer=[]

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logger.debug("opening")
        self.write_message(jsondata('hello'))

    def on_message(self, message):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logger.debug("message received")
        self.write_message("Received from client: {0}".format(message))
        print message
        if message == 'iwantmsg':
            self.write_message(jsondata(''.join(MSG)))
            observer.append(self)

    def on_close(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logger.debug("closing")
        observer.remove(self)

def main():
  parse_command_line()
  wsgi_app = wsgi.WSGIContainer(django.core.handlers.wsgi.WSGIHandler())
  mapping = [ ('/hello', HelloHandler),
              ('/cmd', CommandHandler),
              ('/ws', SocketHandler),
              ('/static/(.*)', web.StaticFileHandler, {'path': "/root/fuheng/tornado-django/blog/static"}),
              ('.*', web.FallbackHandler, dict(fallback=wsgi_app)),
  ]
  tornado_app = web.Application(mapping, debug=True)
  server = httpserver.HTTPServer(tornado_app)
  server.listen(options.port)
  print "Listening at port", options.port
  ioloop.IOLoop.instance().start()

def run_command(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')

def thread_run():
  for line in run_command(CMD):
    print line,
    [i.write_message(jsondata(line)) for i in observer if i is not None]
    MSG.append(line)


if __name__ == '__main__':
  import threading
  #cmd=sys.argv[1:][0]
  #CMD = cmd.split()
  threading.Thread(target=thread_run).start()
  main()
