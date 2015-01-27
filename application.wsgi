#!/usr/bin/env python

from __future__ import absolute_import
from datetime import datetime

from akiri.framework import GenericWSGIApplication
from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware

class LicensingApplication(GenericWSGIApplication):
   
   def service_GET(self, req):
      return {}

   def service_POST(self, req):
      return {}


class HelloApplication(GenericWSGIApplication):
   
   def service_GET(self, req):
      # This could be tracked :).
      return str(datetime.now())

database = 'postgresql://palette:palpass@localhost/licensedb'
check = SessionMiddleware(database, app=LicensingApplication())

application = Router()
application.add_route('/hello\Z', HelloApplication())
application.add_route('/check\Z', check)

if __name__ == '__main__':
   from akiri.framework.server import runserver

   application.add_redirect('/\Z', 'http://www.palette-software.com')
   runserver(application, use_reloader=True)
