#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

import stripe
# stripe.api_key = 'sk_test_ynEoVFrJuhuZ2cVmhCu0ePU4'
stripe.api_key = 'sk_live_VQnPZ5WlUY0hgbYv5KsGUM80'

from datetime import datetime
from webob import exc
import urllib
import logging

from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware
from akiri.framework.sqlalchemy import create_engine, get_session
from akiri.framework.util import required_parameters

from application import BaseApp
from register import RegisterApplication, VerifyApplication
from subscribe import SubscribeApplication
from trial import TrialRequestApplication, TrialStartApplication

from salesforce_api import SalesforceAPI

# pylint: disable=unused-import
from stage import Stage
from licensing import License
from support import Support
from system import System
from product import Product
from server_info import ServerInfo

# currently is set to 'trust' for the loopback interface so use the old pw.
DATABASE = 'postgresql://palette:palpass@localhost/licensedb'

class SupportApplication(BaseApp):

    def service_GET(self, req):
        if 'key' not in req.params:
            # Return 404 instead of bad request to 'hide' this URL.
            return exc.HTTPNotFound()
        entry = License.get_by_key(req.params['key'])
        if entry is None:
            raise exc.HTTPNotFound()
        session = get_session()
        entry.support_contact_time = datetime.utcnow()
        session.commit()
        if not entry.support or not entry.support.active:
            raise exc.HTTPNotFound()
        return {'port': entry.support.port}


class ExpiredApplication(BaseApp):

    def __init__(self, base_url):
        super(ExpiredApplication, self).__init__()
        self.base_url = base_url

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # FIXME: take 'key' and resolve.
        raise exc.HTTPTemporaryRedirect(location=self.base_url)


class HelloApplication(BaseApp):

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # This could be tracked :).
        return str(datetime.now())

def update_add(update, sfkey, opportunity, param, data):
    """Builds a Saleforce Opportunity update."""
    if param in data:
        value = data[param]
        if opportunity[sfkey] != value:
            update[sfkey] = value
            return True
    return False

class LicenseApplication(BaseApp):
    """This application responds to the controller 'license verify'"""

    @required_parameters('system-id', 'license-key',
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Invalid license key: ' + key)
            raise exc.HTTPNotFound()

        update = {}

        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            logger.error('System id from request {1} doesn\'t match DB {2}'\
                         .format(key, system_id, entry.system_id))
            entry.system_id = system_id
            update['System_ID__c'] = system_id

        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            logger.error('License type from request {1} doesn\'t match DB {2}'\
                         .format(key, license_type, entry.type))
            entry.type = license_type
            update['Tableau_App_License_Type__c'] = license_type

        license_quantity = req.params_getint('license-quantity', default=0)
        if entry.n and entry.n != license_quantity:
            logger.error('License quantity {1} doesn\'t match DB {2}'\
                         .format(key, license_quantity, entry.n))
            entry.n = license_quantity
            update['Tableau_App_License_Count__c'] = license_quantity

        logger.info('Updating license information for %s', key)

        entry.contact_time = datetime.utcnow()
        session = get_session()
        session.commit()

        data = {'id': entry.id,
                'trial': entry.istrial(),
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

        sf = SalesforceAPI.connect()
        opportunity = SalesforceAPI.get_opportunity_by_key(sf, key)
        if opportunity is None:
            logger.error("No opportunity for %s : %s", entry.name, key)
            return data

        update_add(update,
                   'Palette_Version__c', opportunity, 
                   'palette-version', req.params)
        update_add(update,
                   'Tableau_App_Version__c', opportunity, 
                   'tableau-version', req.params)
        update_add(update,
                   'Primary_UUID__c', opportunity,
                   'primary-uuid', req.params)
        update_add(update,
                   'Tableau_OS_Bit__c', opportunity,
                   'processor-bitness', req.params)
        update_add(update,
                   'Processor_Type__c', opportunity,
                   'processor-type', req.params)
        update_add(update,
                   'Processor_Count__c', opportunity,
                   'processor-count', req.params)
        update_add(update,
                   'Tableau_OS_Version__c', opportunity,
                   'primary-os-version', req.params)
        update_add(update,
                   'Tableau_App_Bit__c', opportunity,
                   'tableau-bitness', req.params)

        if 'agent-info' in req.params:
            logger.info('%s: %s', key, str(req.params['agent-info']))

        if update:
            sf.Opportunity.update(opportunity['Id'], update)

        return data


# pylint: disable=invalid-name
database = DATABASE
create_engine(database, echo=False, pool_size=20, max_overflow=30)

# Setup logging
logger = logging.getLogger('licensing')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(\
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

router = Router()
# used to test connectivity by the VM - particularly in the setup page.
router.add_route(r'/hello\Z', HelloApplication())
# license verify from the conductor
router.add_route(r'/license\Z', LicenseApplication())
# support application requst
router.add_route(r'/support\Z', SupportApplication())
# UX redirects for expiration
router.add_route(r'/trial-expired\Z', SubscribeApplication())
router.add_route(r'/license-expired\Z', SubscribeApplication())
# GET redirects for the BUY|SUBSCRIBE button and POST handler
router.add_route(r'/buy\Z|/subscribe\Z', SubscribeApplication())

# register a user into the licensing system
router.add_route(r'/api/register\Z', RegisterApplication())
# verify a user into the licensing system
router.add_route(r'/api/verify\Z', VerifyApplication())
# submit (POST) handler for the website /trial form.
router.add_route(r'/api/trial\Z', TrialRequestApplication())
# called when the initial setup page is completed.
router.add_route(r'/api/trial-start\Z', TrialStartApplication())
router.add_redirect(r'/\Z', 'http://www.palette-software.com')

application = SessionMiddleware(app=router)

if __name__ == '__main__':
    import argparse
    from akiri.framework.server import runserver
    from paste.translogger import TransLogger

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--pem', '--ssl-pem', default=None)
    args = parser.parse_args()

    application = TransLogger(application)

    runserver(application, use_reloader=True,
              host='0.0.0.0', port=args.port, ssl_pem=args.pem)
