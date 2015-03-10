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

import boto.route53

from stage import Stage
from licensing import License
from system import System
from support import Support
from utils import strip_scheme, server_name
from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI
from ansible_api import AnsibleAPI

#DATABASE = 'postgresql://palette:palpass@localhost/licensedb'
DATABASE = 'postgresql://palette:palpass@localhost/ldb'

def time_from_today(hours=0, days=0, months=0):
    return datetime.utcnow() + \
           relativedelta(hours=hours, days=days, months=months)

def kvp(key, value):
    if value is not None:
        return str(key) + '=' + urllib.quote(str(value))
    else:
        return str(key) + '='

def translate_values(source, entry, fields):
    """Convert fields values to the appropriate values in the entry."""
    for name, dest_attr in fields.items():
        value = source.get(name)
        if value is not None:
            setattr(entry, dest_attr, value)

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


def get_unique_name(name):
    """ Lookup and get a unique name for the server based on
        what is already in the database
    """
    count = 1
    to_try = name

    while True:
        result = License.get_by_name(to_try)
        if result is not None:
            # name exists try the next numbered one$
            to_try = '{0}-{1}'.format(name, count)
            count = count + 1
        else:
            break

    return to_try

class TrialRequestApplication(GenericWSGIApplication):
    TRIAL_FIELDS = {'Field133':'firstname',
                    'Field134':'lastname',
                    'Field3':'email',
                    'Field115':'website',
                    'Field128':'hosting_type',
                    'Field130':'aws_zone',
                    'Field131':'promo_code',
                    'Field126':'admin_role'}

    AWS_HOSTING = 'Your AWS Account with our AMI Image'
    VMWARE_HOSTING = 'Your Data Center with our VMware Image'
    PCLOUD_HOSTING = 'Palette Online in our Data Center'

    @required_parameters('Field133',
                         'Field134',
                         'Field3',
                         'Field115',
                         'Field128',
                         'Field130',
                         'Field131',
                         'Field126')
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        firstname = req.params['Field133']
        lastname = req.params['Field134']
        fullname = firstname + " " + lastname
        email = req.params['Field3']
        website = req.params['Field115']

        logger.info('New trial request for {0} {1} {2}'\
              .format(website, fullname, email))

        entry = License()
        translate_values(req.params, entry,
                         TrialRequestApplication.TRIAL_FIELDS)
        entry.name = website
        entry.key = str(uuid.uuid4())
        entry.expiration_time = time_from_today(
            days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
        entry.stageid = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id
        entry.trial = True #FIXME
        entry.organization = server_name(strip_scheme(entry.website))
        entry.subdomain = get_unique_name(entry.organization)
        entry.name = entry.subdomain
        entry.website = strip_scheme(entry.website)

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
        elif entry.hosting_type == TrialRequestApplication.PCLOUD_HOSTING:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-PCLOUD-ID')
        else:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-DONTKNOW-ID')
        SendwithusAPI.subscribe_user(mailid, entry)

        if entry.hosting_type == TrialRequestApplication.PCLOUD_HOSTING:
            AnsibleAPI.launch_instance(entry,
                     System.get_by_key('PALETTECLOUD-LAUNCH-SUCCESS-ID'),
                     System.get_by_key('PALETTECLOUD-LAUNCH-FAIL-ID'))

        SlackAPI.notify('Trial request from: '
                '{0} ({1}) Org: {2} - Type: {3}'.format(
                entry.firstname + ' ' + entry.lastname, entry.email,
                entry.organization, entry.hosting_type))

        logger.info('Trial request success for {0} {1}'\
                    .format(entry.email, entry.key))

        return {'license-key' :entry.key}

class TrialRegisterApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key',
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
        entry.expiration_time = time_from_today(
             days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
        entry.registration_start_time = datetime.utcnow()
        entry.contact_time = datetime.utcnow()
        session = get_session()
        session.commit()

        # update the opportunity
        SalesforceAPI.update_opportunity(entry)
        # subscribe the user to the trial workflow if not already
        SendwithusAPI.subscribe_user(
              System.get_by_key('SENDWITHUS-TRIAL-REGISTERED-ID'), entry)

        logger.info('Trial Registration for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

        return {'trial': True,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

class TrialStartApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key',
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
            SendwithusAPI.subscribe_user(
                 System.get_by_key('SENDWITHUS-TRIAL-STARTED-ID'), entry)

            SlackAPI.notify('Trial Started: '
                    'Key: {0}, Name: {1} ({2}), Org: {3}, Type: {4}' \
                    .format(entry.key,
                    entry.firstname + ' ' + entry.lastname, entry.email,
                    entry.organization, entry.hosting_type))
        else:
            logger.info('Licensing ping received for key {0}'.format(key))
            # just update the last contact time
            entry.contact_time = datetime.utcnow()
            session.commit()

        return {'trial': entry.trial,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

class BuyRequestApplication(GenericWSGIApplication):
    """ Class that Handles get/post methods for the palette buy url
    """

    # field mapping between request parameters and entity parameters
    # on the buy form
    BUY_FIELDS = {'Field3':'firstname',
                  'Field4':'lastname',
                  'Field6':'website',
                  'Field5':'email',
                  'Field21':'phone',
                  'Field22':'palette_type',
                  'Field8':'license_type',
                  'Field9':'license_cap',
                  'Field13':'billing_address_line1',
                  'Field14':'billing_address_line2',
                  'Field15':'billing_city',
                  'Field16':'billing_state',
                  'Field17':'billing_zip',
                  'Field18':'billing_country',
                  'Field330':'amount'}

    # additional mapping when alt_billing is set
    ALT_BILLING_FIELDS = {'Field11':'billing_fn',
                          'Field12':'billing_ln',
                          'Field20':'billing_email',
                          'Field19':'billing_phone'}

    NAMED_USER_TYPE = 'Named-user'
    CORE_USER_TYPE = 'Core'

    def calculate_price(self, count, license_type):
        val = 0
        if license_type == BuyRequestApplication.NAMED_USER_TYPE:
            val = int(System.get_by_key('USER-PRICE')) * count
        elif license_type == BuyRequestApplication.CORE_USER_TYPE:
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

        fields = {'field7':entry.key, 'field3':entry.firstname,
                  'field4':entry.lastname, 'field5':entry.email,
                  'field6':entry.website, 'field21':entry.phone}
        url_items = [kvp(k, v) for k, v in fields.iteritems()]
        url = '&'.join(url_items)
        location = '{0}/{1}'.format(System.get_by_key('BUY-URL'), url)
        raise exc.HTTPTemporaryRedirect(location=location)

    @required_parameters('Field3', 'Field4', 'Field6', 'Field5', 'Field21',
                         'Field22',
                         'Field13', 'Field14', 'Field15', 'Field16',
                         'Field17', 'Field18', 'Field225',
                         'Field11', 'Field12', 'Field20', 'Field19',
                         'Field7')
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

        translate_values(req.params, entry,
                         BuyRequestApplication.BUY_FIELDS)
        translate_values(req.params, entry,
                         BuyRequestApplication.ALT_BILLING_FIELDS)

        if req.params['Field225'] == 'Yes! Let me tell you more!':
            entry.alt_billing = True

        entry.expiration_time = time_from_today(
            months=int(System.get_by_key('BUY-EXPIRATION-MONTHS')))
        entry.license_start_time = datetime.utcnow()
        entry.stageid = Stage.get_by_key('STAGE-CLOSED-WON').id
        session = get_session()
        session.commit()

        # update the opportunity
        SalesforceAPI.update_contact(entry)
        SalesforceAPI.update_opportunity(entry)
        # subscribe the user to the trial workflow if not already
        SendwithusAPI.subscribe_user(
            System.get_by_key('SENDWITHUS-CLOSED-WON-ID'), entry)

        SendwithusAPI.send_message(
            System.get_by_key('SENDWITHUS-BUY-NOTIFICATION-ID'),
            'licensing@palette-software.com',
            'hello@palette-software.com',
            {'firstname':entry.firstname,
             'lastname':entry.lastname,
             'email':entry.email,
             'phone':entry.phone,
             'org':entry.organization,
             'hosting_type':entry.hosting_type,
             'amount':entry.amount,
             'billing_address_line1':entry.billing_address_line1,
             'billing_address_line2':entry.billing_address_line2,
             'billing_city':entry.billing_city,
             'billing_state':entry.billing_state,
             'billing_zip':entry.billing_zip,
             'billing_country':entry.billing_country
             })

        SlackAPI.notify('Buy request from: '
                '{0} ({1}) Org: {2} - Type: {3}'.format(\
                entry.firstname + ' ' + entry.lastname, entry.email,
                entry.website, entry.hosting_type))

        logger.info('Buy request success for {0}'.format(key))

class CheckNameApplication(GenericWSGIApplication):
    @required_parameters('hostname', allowed_methods=['GET'])
    def service_GET(self, req):
        """ Checks to see if an supplied hostname exists in Route 53
        """
        hostname = req.params['hostname']
        dnszone = System.get_by_key('PALETTECLOUD-DNS-ZONE')
        conn = boto.route53.connect_to_region('universal')
        zone = conn.get_zone(dnszone)
        result = zone.find_records(hostname + '.' + dnszone, 'CNAME', all=True)
        exists = result is not None

        return {'hostname':hostname, 'exists': exists}

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
router.add_route(r'/hello\Z', HelloApplication())
router.add_route(r'/license\Z', TrialStartApplication())
router.add_route(r'/support\Z', SupportApplication())
router.add_route(r'/trial-expired\Z', BuyRequestApplication())
router.add_route(r'/license-expired\Z', BuyRequestApplication())
router.add_route(r'/buy\Z', BuyRequestApplication())

router.add_route(r'/api/trial_request\Z|/api/trial\Z',
                 TrialRequestApplication())
router.add_route(r'/api/trial_register\Z', TrialRegisterApplication())
router.add_route(r'/api/trial_start\Z', TrialStartApplication())
router.add_route(r'/api/buy_request', BuyRequestApplication())
router.add_route(r'/api/check_name\Z', CheckNameApplication())

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

    router.add_redirect(r'/\Z', 'http://www.palette-software.com')
    runserver(application, use_reloader=True,
              host='0.0.0.0', port=args.port, ssl_pem=args.pem)
