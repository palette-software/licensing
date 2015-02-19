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
from support import Support

# FIXME: https
LICENSE_EXPIRED = 'http://www.palette-software.com/license-expired'
TRIAL_EXPIRED = 'http://www.palette-software.com/trial-expired'
BUY = 'http://www.palette-software.com/buy'

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

class SupportApplication(GenericWSGIApplication):

    def service_GET(self, req):
        if 'key' not in req.params:
            # Return 404 instead of bad request to 'hide' this URL.
            return exc.HTTPNotFound()
        entry = Support.find_active_port_by_key(req.params['key'])
        if entry is None:
            raise exc.HTTPNotFound()
        return {'port': entry.port}


class ExpiredApplication(GenericWSGIApplication):

    def __init__(self, base_url):
        super(ExpiredApplication, self).__init__()
        self.base_url = base_url

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # FIXME: take 'key' and resolve.
        raise exc.HTTPTemporaryRedirect(location=self.base_url)


class HelloApplication(GenericWSGIApplication):

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # This could be tracked :).
        return str(datetime.now())


# pylint: disable=invalid-name
database = 'postgresql://palette:palpass@localhost/licensedb'
create_engine(database, echo=False, pool_size=20, max_overflow=50)

router = Router()
router.add_route(r'/hello\Z', HelloApplication())
router.add_route(r'/license\Z', LicensingApplication())
router.add_route(r'/support\Z', SupportApplication())
router.add_route(r'/trial-expired\Z', ExpiredApplication(TRIAL_EXPIRED))
router.add_route(r'/license-expired\Z', ExpiredApplication(LICENSE_EXPIRED))
router.add_route(r'/buy\Z', ExpiredApplication(BUY))

application = SessionMiddleware(router)

if __name__ == '__main__':
    from akiri.framework.server import runserver

    router.add_redirect(r'/\Z', 'http://www.palette-software.com')
    runserver(application, use_reloader=True)
