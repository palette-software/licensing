#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

from datetime import datetime
from webob import exc
import urllib
import logging

from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware
from akiri.framework.sqlalchemy import create_engine, get_session
from akiri.framework.util import required_parameters

from application import BaseApp
from trial import TrialRequestApplication, TrialStartApplication

from slack_api import SlackAPI

# pylint: disable=unused-import
from stage import Stage
from licensing import License
from system import System

# currently is set to 'trust' for the loopback interface so use the old pw.
DATABASE = 'postgresql://palette:palpass@localhost/licensedb'

class UnreachableApplication(BaseApp):
    """The user's browser is sent to this URI when their server can't contact
    licensing for an extended period of time.  The hope is that the user will
    be able to talk to licensing even if their server can't."""

    @required_parameters('key', allowed_methods=['GET'])
    def service_GET(self, req):
        key = req.params['key']

        location = System.get_by_key('LICENSING-UNREACHABLE-URL')

        entry = License.get_by_key(key)
        if not entry:
            SlackAPI.warn("(unreachable) key not found: " + key)
            raise exc.HTTPTemporaryRedirect(location=location)

        # FIXME: prevent multiple Slack messages...
        SlackAPI.error("'{0}' cannot reach licensing.".format(entry.name))
        raise exc.HTTPTemporaryRedirect(location=location)


class HelloApplication(BaseApp):

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # This could be tracked :).
        return str(datetime.now())


def get_license_quantity(req):
    # FIXME
    if 'license-core-licenses' in req.params:
        return req.params_getint('license-core-licenses')
    if not 'license-quantity' in req.params:
        return None
    return req.params_getint('license-quantity')

class LicenseApplication(BaseApp):
    """This application responds to the controller 'license verify'"""

    @required_parameters('system-id', 'license-key')
    def service_POST(self, req):
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Invalid license key: ' + key)
            raise exc.HTTPNotFound()

        update = {}

        system_id = req.params['system-id']
        if entry.system_id != system_id:
            if entry.system_id:
                logger.error('%s: System id from %s != DB %s',
                             key, system_id, entry.system_id)
            entry.system_id = system_id
            update['System_ID__c'] = system_id

        if 'license-type' in req.params:
            license_type = req.params['license-type']
            if entry.type != license_type:
                if entry.type:
                    logger.error('%s: License type %s != DB %s',
                                 key, license_type, entry.type)
                    entry.type = license_type
                    update['Tableau_App_License_Type__c'] = license_type

        license_quantity = get_license_quantity(req)
        if not license_quantity is None:
            if entry.n != license_quantity:
                if entry.n:
                    logger.error('%s: License quantity %s != DB %s',
                                 key, license_quantity, entry.n)
                entry.n = license_quantity
                update['Tableau_App_License_Count__c'] = license_quantity
        else:
            # SlackAPI.error(key + ': Invalid license quantity')
            # The can happen after an upgrade if the primary is not connected.
            logger.warning(key + ': Invalid license quantity')

        entry.contact_time = datetime.utcnow()
        session = get_session()
        session.commit()

        # Enable full POST logging for now
        logger.info('%s[%s]: %s', entry.name, key, str(req.params))

        data = {'id': entry.id,
                'trial': entry.istrial(),
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

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
# called when the initial setup page is completed.
router.add_route(r'/api/trial-start\Z', TrialStartApplication())

router.add_redirect(r'/\Z', 'http://www.palette-software.com')

unreachable = UnreachableApplication()
router.add_route(r'/unreachable\Z|/licensing-unreachable\Z', unreachable)
router.add_route(r'/licensing-unavailable\Z', unreachable) # old name

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
