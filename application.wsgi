#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

from datetime import datetime, timedelta
from webob import exc
import uuid

from akiri.framework import GenericWSGIApplication
from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware
from akiri.framework.sqlalchemy import create_engine, get_session
from akiri.framework.util import required_parameters

from licensing import License
from support import Support
from mailchimp_api import MailchimpAPI
from salesforce_api import SalesforceAPI

import config

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

    @required_parameters('key')
    def service_GET(self, req):
        port = Support.find_active_port_by_key(req.params['key'])
        if port is None:
            raise exc.HTTPNotFound()
        return {'port': port}


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

class TryPaletteApplication(GenericWSGIApplication):
    def service_POST(self, req):
        """
        """
        fn = req.params['Field1']
        ln = req.params['Field2']
        fullname = fn + " " + ln
        email = req.params['Field3']
        phone = req.params['Field113']
        org = req.params['Field6']
        website = req.params['Field115']
        timezone = req.params['Field7']
        hosting_type = req.params['Field8']
        subdomain = req.params['Field9']
        timezone = req.params['Field7']
        license_type = None
        stage = config.SF_STAGE1

        key = str(uuid.uuid4())
        exp_time = datetime.today() + \
                   timedelta(days=config.REGISTERED_EXPIRATION_DAYS)

        data = {'key':key, 'fn': fn, 'ln':ln, 'fullname': fullname, \
                'phone': phone, 'email':email, \
                'subdomain':subdomain, 'org':org, 'timezone': timezone, \
                'website':website, 'hosting_type':hosting_type, \
                'exp_time': exp_time, 'stage':stage}

        # fixme add exception handling
        entry = License()
        entry.set_license_info(data)

        session = get_session()
        session.add(entry)
        session.commit()

        # create or use an existing opportunity
        SalesforceAPI.salesforce_new_opportunity(data)

        # subscribe the user to the trial workflow if not already
        MailchimpAPI.subscribe_user(config.MAILCHIMP_TRIAL_REGISTERED_TITLE, \
                                    data)

        return "Trial Started"

# pylint: disable=invalid-name
create_engine(config.DB_URL, echo=False)

router = Router()
router.add_route(r'/hello\Z', HelloApplication())
router.add_route(r'/license\Z', LicensingApplication())
router.add_route(r'/support\Z', SupportApplication())
router.add_route(r'/trial-expired\Z', ExpiredApplication(TRIAL_EXPIRED))
router.add_route(r'/license-expired\Z', ExpiredApplication(LICENSE_EXPIRED))
router.add_route(r'/buy\Z', ExpiredApplication(BUY))
router.add_route(r'/api/palette/try_palette', TryPaletteApplication())

application = SessionMiddleware(config.DB_URL, app=router)

if __name__ == '__main__':
    from akiri.framework.server import runserver

    router.add_redirect(r'/\Z', 'http://www.palette-software.com')
    runserver(application, use_reloader=True, host='0.0.0.0')
