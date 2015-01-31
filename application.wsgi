#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

from datetime import datetime
from webob import exc

from akiri.framework import GenericWSGIApplication
from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware
from akiri.framework.sqlalchemy import create_engine, get_session
from akiri.framework.util import required_parameters

from licensing import License

class LicensingApplication(GenericWSGIApplication):

    @required_parameters('system-id', 'license-key', \
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()
        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            # FIXME: notify
            pass
        entry.system_id = system_id
        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            # FIXME: notify
            pass
        entry.type = license_type
        license_quantity = req.params['license-quantity']
        if entry.n and entry.n != license_quantity:
            # FIXME: notify
            pass
        entry.n = license_quantity
        session = get_session()
        session.commit()
        return {'trial': entry.trial,
                'expiration-time': str(entry.expiration_time)}
        

class HelloApplication(GenericWSGIApplication):

    def service_GET(self, req):
        # This could be tracked :).
        return str(datetime.now())

database = 'postgresql://palette:palpass@localhost/licensedb'
create_engine(database, echo=False)
license_app = SessionMiddleware(database, app=LicensingApplication())

application = Router()
application.add_route(r'/hello\Z', HelloApplication())
application.add_route(r'/license\Z', license_app)

if __name__ == '__main__':
    from akiri.framework.server import runserver

    application.add_redirect(r'/\Z', 'http://www.palette-software.com')
    runserver(application, use_reloader=True)
