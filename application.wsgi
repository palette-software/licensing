#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

from datetime import datetime
from dateutil.relativedelta import relativedelta
from webob import exc
import uuid
import urllib
from decimal import Decimal
import logging

from akiri.framework import GenericWSGIApplication
from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware
from akiri.framework.sqlalchemy import create_engine, get_session
from akiri.framework.util import required_parameters

from stage import Stage
from licensing import License
from system import System
from support import Support
from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from util import str2bool
from slack_api import SlackAPI

import config

# FIXME: https
LICENSE_EXPIRED = 'http://www.palette-software.com/license-expired'
TRIAL_EXPIRED = 'http://www.palette-software.com/trial-expired'
BUY = 'http://www.palette-software.com/buy'

def time_from_today(hours=0, days=0, months=0):
    return datetime.utcnow() + \
           relativedelta(hours=hours, days=days, months=months)

def kvp(k, v):
    if v is not None:
        return str(k) + '=' + urllib.quote(str(v))
    else:
        return str(k) + '='

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

class TrialRequestApplication(GenericWSGIApplication):
    TRIAL_FIELDS = {'Field1':'firstname', 'Field2':'lastname', \
                    'Field3':'email', \
                    'Field6':'organization', 'Field115':'website', \
                    'Field8':'hosting_type', 'Field9':'subdomain', \
                    'Field120':'admin_role'}

    AWS_HOSTING = 'Your AWS Account with our AMI Image'
    VMWARE_HOSTING = 'Your Data Center with our VMware Image'

    @required_parameters('Field1', 'Field2', 'Field3', 'Field6', 'Field115', \
                         'Field8', 'Field9', 'Field120')
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        fn = req.params['Field1']
        ln = req.params['Field2']
        fullname = fn + " " + ln
        email = req.params['Field3']
        org = req.params['Field6']

        logger.info('New trial request for {0} {1} {2}'\
              .format(org, fullname, email))

        entry = License()
        entry.set_values(req.params, entry, \
           TrialRequestApplication.TRIAL_FIELDS)
        entry.name = org
        entry.key = str(uuid.uuid4())
        entry.expiration_time = time_from_today(\
            days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
        entry.stageid = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id

        session = get_session()
        session.add(entry)
        session.commit()

        # create or use an existing opportunity
        SalesforceAPI.new_opportunity(entry)
        # subscribe the user to the trial list 
        if entry.hosting_type == TrialRequestApplication.AWS_HOSTING:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-ID')
        elif entry.hosting_type == TrialRequestApplication.VMWARE_HOSTING:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-VMWARE-ID')
        else:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-PCLOUD-ID')
        SendwithusAPI.subscribe_user(mailid, entry)

        if str2bool(System.get_by_key('SEND-SLACK')) == True:
            SlackAPI.notify('Trial request from: '
                    '{0} ({1}) Org: {2} - Type: {3}'.format(\
                    entry.firstname + ' ' + entry.lastname, entry.email, \
                    entry.organization, entry.hosting_type))

        logger.info('Trial request success for {0} {1}'\
                    .format(entry.email, entry.key))

        return {'license-key' :entry.key}

class TrialRegisterApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key', \
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        """ Handle a Trial Registration
        """
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()

        #if entry.stage is not config.SF_STAGE_TRIAL_REQUESTED:
        #    raise exc.HTTPTemporaryRedirect(location=config.BAD_STAGE_URL)

        logger.info('Processing Trial Registration for key {0}'.format(key))
        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            logger.error('Invalid trial register request for key {0}.'
                         'System id from request {1} doesnt match DB {2}'\
                   .format(key, system_id, entry.system_id))
        entry.system_id = system_id

        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            logger.error('Invalid trial register request for key {0}.'
                         'License type from request {1} doesnt match DB {2}'\
                   .format(key, license_type, entry.type))
        entry.type = license_type

        license_quantity = req.params['license-quantity']
        if entry.n and entry.n != license_quantity:
            logger.error('Invalid trial register request for key {0}.'
                       'License quantity from request {1} doesnt match DB {2}'\
                   .format(key, license_quantity, entry.n))
        entry.n = license_quantity

        entry.stageid = Stage.get_by_key('STAGE-TRIAL-REGISTERED').id
        entry.expiration_time = time_from_today(\
             days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
        entry.registration_start_time = datetime.utcnow()
        entry.contact_time = datetime.utcnow()
        session = get_session()
        session.commit()

        # update the opportunity
        SalesforceAPI.update_opportunity(entry)
        # subscribe the user to the trial workflow if not already
        SendwithusAPI.subscribe_user(\
              System.get_by_key('SENDWITHUS-TRIAL-REGISTERED-ID'), entry)

        logger.info('Trial Registration for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

        return {'trial': True,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

class TrialStartApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key', \
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        """ Handle a Trial start
        """
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()

        #if entry.stage is not config.SF_STAGE_TRIAL_REGISTERED:
        #    raise exc.HTTPTemporaryRedirect(location=config.BAD_STAGE_URL)

        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            logger.error('Invalid trial start request for key {0}.' 
                         'System id from request {1} doesnt match DB {2}'\
                   .format(key, system_id, entry.system_id))
        entry.system_id = system_id

        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            logger.error('Invalid trial start request for key {0}. '
                         'License Type from request {1} doesnt match DB {2}'\
                   .format(key, license_type, entry.type))
        entry.type = license_type

        license_quantity = int(req.params['license-quantity'])
        if entry.n and entry.n != license_quantity:
            logger.error('Invalid trial start request for key {0}. '
                         'License Type from request {1} doesnt match DB {2}'\
                   .format(key, license_quantity, entry.n))
        entry.n = license_quantity

        session = get_session()

        if entry.stageid != Stage.get_by_key('STAGE-TRIAL-STARTED').id:
            logger.info('Starting Trial for key {0}'.format(key))

            # if this is the trial hasnt started yet start it
            entry.stageid = Stage.get_by_key('STAGE-TRIAL-STARTED').id
            entry.expiration_time = time_from_today(\
                days=int(System.get_by_key('TRIAL-REG-EXPIRATION-DAYS')))
            entry.trial_start_time = datetime.utcnow()
            entry.contact_time = entry.trial_start_time 
            session.commit()

            logger.info('Trial Start for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

            # update the opportunity
            SalesforceAPI.update_opportunity(entry)
            # subscribe the user to the trial workflow if not already
            SendwithusAPI.subscribe_user(\
                 System.get_by_key('SENDWITHUS-TRIAL-STARTED-ID'), entry)
        else:
            logger.info('Licensing ping received for key {0}'.format(key))
            # just update the last contact time
            entry.contact_time = datetime.utcnow()
            session.commit()

        return {'trial': True,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

class BuyRequestApplication(GenericWSGIApplication):
    """ Class that Handles get/post methods for the palette buy url
    """

    # field mapping between request parameters and entity parameters
    # on the buy form
    BUY_FIELDS = {'Field3':'firstname', \
                  'Field4':'lastname', \
                  'Field6':'organization', \
                  'Field5':'email', \
                  'Field21':'phone', \
                  'Field22':'palette_type', \
                  'Field8':'license_type', \
                  'Field9':'license_cap', \
                  'Field13':'billing_address_line1', \
                  'Field14':'billing_address_line2', \
                  'Field15':'billing_city', \
                  'Field16':'billing_state', \
                  'Field17':'billing_zip', \
                  'Field18':'billing_country', \
                  'Field330':'amount'}

    # additional mapping when alt_billing is set
    ALT_BILLING_FIELDS = {'Field11':'billing_fn', \
                          'Field12':'billing_ln', \
                          'Field20':'billing_email', \
                          'Field19':'billing_phone'}

    NAMED_USER_TYPE = 'Named-user'
    CORE_USER_TYPE = 'Core'

    def calculate_price(self, count, type):
        val = 0
        if type == BuyRequestApplication.NAMED_USER_TYPE:
            val = int(System.get_by_key('USER-PRICE')) * count
        elif type == BuyRequestApplication.CORE_USER_TYPE:
            val = int(System.get_by_key('CORE-PRICE')) * count
        return Decimal(val)

    def service_GET(self, req):
        """ Handle get request which looks up the key and redirects to a
            URL to buy with the info pre-populated on the form
        """
        key = req.params_get('key')
        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Buy request get count not find {0}'.format(key))
            raise exc.HTTPNotFound()

        #if entry.stage is not config.SF_STAGE_TRIAL_STARTED:
        #    raise exc.HTTPTemporaryRedirect(location=config.BAD_STAGE_URL)

        logger.info('Processing Buy get request info for {0}'.format(key))

        amount = self.calculate_price(entry.n, entry.type)

        fields = {'field7':entry.key, 'field3':entry.firstname, \
                  'field4':entry.lastname, 'field5':entry.email, \
                  'field6':entry.organization, 'field21':entry.phone, \
                  'field9':entry.n, 'field330':amount}
        url_items = [kvp(k, v) for k, v in fields.iteritems()]
        url = '&'.join(url_items)
        location = '{0}/{1}'.format(System.get_by_key('BUY-URL'), url)
        raise exc.HTTPTemporaryRedirect(location=location)

    @required_parameters('Field3', 'Field4', 'Field6', 'Field5', 'Field21',
                         'Field22', 'Field8', 'Field9', \
                         'Field13', 'Field14', 'Field15', 'Field16', \
                         'Field17', 'Field18', 'Field225', \
                         'Field11', 'Field12','Field20', 'Field19', \
                         'Field7', 'Field330')
    def service_POST(self, req):
        """ Handle a Buy Request
        """
        key = req.params['Field7']
        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Buy request post could not find {0}'.format(key))
            raise exc.HTTPNotFound()

        #if entry.stage is not config.SF_STAGE_TRIAL_STARTED:
        #    raise exc.HTTPTemporaryRedirect(location=config.BAD_STAGE_URL)

        logger.info('Processing Buy Post request for {0}'.format(key))

        entry.set_values(req.params, entry, \
                         BuyRequestApplication.BUY_FIELDS)
        entry.set_values(req.params, entry, \
                         BuyRequestApplication.ALT_BILLING_FIELDS)

        if req.params['Field225'] == 'Yes! Let me tell you more!':
            entry.alt_billing = True

        entry.expiration_time = time_from_today(\
            months=int(System.get_by_key('BUY-EXPIRATION-MONTHS')))
        entry.license_start_time = datetime.utcnow()
        entry.stageid = Stage.get_by_key('TRIAL-CLOSED-WON').id
        session = get_session()
        session.commit()

        # update the opportunity
        SalesforceAPI.update_opportunity(entry)
        # subscribe the user to the trial workflow if not already
        SendwithusAPI.subscribe_user(\
            System.get_by_key('SENDWITHUS-CLOSED-WON-ID'), entry)

        logger.info('Buy request success for {0}'.format(key))

# pylint: disable=invalid-name
create_engine(config.db_url, echo=False, pool_size=20, max_overflow=50)

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
router.add_route(r'/hello\Z', HelloApplication())
router.add_route(r'/license\Z', TrialStartApplication())
router.add_route(r'/support\Z', SupportApplication())
router.add_route(r'/trial-expired\Z', ExpiredApplication(TRIAL_EXPIRED))
router.add_route(r'/license-expired\Z', ExpiredApplication(LICENSE_EXPIRED))
router.add_route(r'/buy\Z', BuyRequestApplication())

router.add_route(r'/api/trial_request\Z', TrialRequestApplication())
router.add_route(r'/api/trial_register\Z', TrialRegisterApplication())
router.add_route(r'/api/trial_start\Z', TrialStartApplication())
router.add_route(r'/api/buy_request', BuyRequestApplication())

application = SessionMiddleware(app=router)

if __name__ == '__main__':
    from akiri.framework.server import runserver

    router.add_redirect(r'/\Z', 'http://www.palette-software.com')
    runserver(application, use_reloader=True, host='0.0.0.0')
