#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

from datetime import datetime
from dateutil.relativedelta import relativedelta
from webob import exc
import uuid
import urllib
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
from utils import get_netloc, server_name, hostname_only
from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI
from ansible_api import AnsibleAPI
from boto_api import BotoAPI

import stripe
#stripe.api_key = 'sk_test_ynEoVFrJuhuZ2cVmhCu0ePU4'
stripe.api_key = 'sk_live_VQnPZ5WlUY0hgbYv5KsGUM80'

DATABASE = 'postgresql://palette:palpass@localhost/licensedb'

def time_from_today(hours=0, days=0, months=0):
    return datetime.utcnow() + \
           relativedelta(hours=hours, days=days, months=months)

def kvp(key, value):
    if value is not None:
        return str(key) + '=' + urllib.quote(str(value))
    else:
        return str(key) + '='

def dict_to_qs(data):
    qstr = '&'.join([kvp(k, v) for k, v in data.iteritems()])
    if not qstr:
        return ''
    return '?' + qstr

def translate_values(source, entry, fields):
    """Convert fields values to the appropriate values in the entry."""
    for name, dest_attr in fields.items():
        value = source.get(name)
        if value is not None:
            setattr(entry, dest_attr, value)

def get_unique_name(name):
    """ Lookup and get a unique name for the server based on
        what is already in the database
        The algorithm comes up with names in this format:
        foo, foo-2, foo-3
    """
    count = 2
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

def populate_email_data(entry):
    """ creates a dict that contains the fileds to put passed to trial emails
    """
    email_data = {'license':entry.key,
                  'firstname':entry.firstname,
                  'lastname':entry.lastname,
                  'organization':entry.organization,
                  'hosting_type':entry.hosting_type,
                  'promo_code':entry.promo_code,
                  'subdomain':entry.subdomain,
                  'access_key':entry.access_key,
                  'secret_key':entry.secret_key}
    return email_data

def populate_buy_email_data(entry):
    """ creates a dict that contains the fileds to put passed to buy emails
    """
    email_data = {'firstname':entry.firstname,
                  'lastname':entry.lastname,
                  'email':entry.email,
                  'phone':entry.phone,
                  'org':entry.organization,
                  'hosting_type':entry.hosting_type,
                  'billing_address_line1':entry.billing_address_line1,
                  'billing_address_line2':entry.billing_address_line2,
                  'billing_city':entry.billing_city,
                  'billing_state':entry.billing_state,
                  'billing_zip':entry.billing_zip,
                  'billing_country':entry.billing_country}
    return email_data

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


class LicenseApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key',
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        """ Handle a Trial Registration
        """
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Invalid license key: ' + key)
            raise exc.HTTPNotFound()

        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            logger.error('System id from request {1} doesnt match DB {2}'\
                         .format(key, system_id, entry.system_id))
        entry.system_id = system_id

        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            logger.error('License type from request {1} doesnt match DB {2}'\
                         .format(key, license_type, entry.type))
        entry.type = license_type

        license_quantity = req.params_getint('license-quantity', default=0)
        if entry.n and entry.n != license_quantity:
            logger.error('License quantity {1} doesn\'t match DB {2}'\
                         .format(key, license_quantity, entry.n))
        entry.n = license_quantity

        entry.contact_time = datetime.utcnow()
        session = get_session()
        session.commit()

        return {'id': entry.id,
                'trial': entry.trial,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}


TRIAL_FIELDS = {
    'fname':'firstname', 'lname':'lastname',
    'email':'email',
    'text-yui_3_10_1_1_1389902554996_16499-field': 'website',
    'radio-yui_3_17_2_1_1407117642911_45717-field':'admin_role',
    'radio-yui_3_17_2_1_1426521445942_51014-field':'hosting_type'
}

class TrialRequestApplication(GenericWSGIApplication):

    TRIAL_FIELDS = TRIAL_FIELDS
    AWS_HOSTING = 'Your AWS Account with our AMI Image'
    VMWARE_HOSTING = 'Your Data Center with our VMware Image'
    PCLOUD_HOSTING = 'Palette Cloud in our Data Center'

    REDIRECT_URL = 'http://www.palette-software.com/trial-confirmation'

    @required_parameters(*TRIAL_FIELDS.keys())
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        entry = License()
        translate_values(req.params, entry, self.TRIAL_FIELDS)
        logger.info('New trial request for %s %s %s %s', entry.website,
                    entry.firstname, entry.lastname, entry.email)
        entry.key = str(uuid.uuid4())
        entry.expiration_time = time_from_today(
            days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
        entry.stageid = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id
        entry.trial = True #FIXME
        entry.website = get_netloc(entry.website).lower()
        entry.organization = server_name(entry.website)
        entry.subdomain = get_unique_name(hostname_only(entry.organization))
        entry.name = entry.subdomain
        print '{0} {1} {2} {3}'.format(entry.website, entry.organization,
                                       entry.subdomain, entry.name)

        entry.aws_zone = BotoAPI.get_region_by_name(entry.aws_zone)
        entry.access_key, entry.secret_key = BotoAPI.create_s3(entry)
        entry.registration_start_time = datetime.utcnow()

        session = get_session()
        session.add(entry)
        session.commit()

        # create or use an existing opportunity
        opp_id = SalesforceAPI.new_opportunity(entry)
        # subscribe the user to the trial list
        if entry.hosting_type == TrialRequestApplication.AWS_HOSTING:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-ID')
        elif entry.hosting_type == TrialRequestApplication.VMWARE_HOSTING:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-VMWARE-ID')
        elif entry.hosting_type == TrialRequestApplication.PCLOUD_HOSTING:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-PCLOUD-ID')
        else:
            mailid = System.get_by_key('SENDWITHUS-TRIAL-REQUESTED-DONTKNOW-ID')
        SendwithusAPI.subscribe_user(mailid,
                                     'hello@palette-software.com',
                                     entry.email,
                                     populate_email_data(entry))

        if entry.hosting_type == TrialRequestApplication.PCLOUD_HOSTING:
            AnsibleAPI.launch_instance(entry,
                     System.get_by_key('PALETTECLOUD-LAUNCH-SUCCESS-ID'),
                     System.get_by_key('PALETTECLOUD-LAUNCH-FAIL-ID'))

        sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
        SlackAPI.notify('Trial request Opportunity: '
                '{0} ({1}) - Type: {2} {3}'.format(
                SalesforceAPI.get_opportunity_name(entry),
                entry.email,
                entry.hosting_type,
                sf_url))

        logger.info('Trial request success for %s %s', entry.email, entry.key)

        # use 302 here so that the browswer redirects with a GET request.
        return exc.HTTPFound(location=self.REDIRECT_URL)


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
                        System.get_by_key('SENDWITHUS-TRIAL-REGISTERED-ID'),
                        'hello@palette-software.com',
                        entry.email,
                        populate_email_data(entry))

        logger.info('Trial Registration for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

        return {'trial': True,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}


class TrialStartApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key')
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

        session = get_session()

        # FIXME: *only* do this if in the correct stage (otherwise free trials!)
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
                         System.get_by_key('SENDWITHUS-TRIAL-STARTED-ID'),
                         'hello@palette-software.com',
                         entry.email,
                         populate_email_data(entry))

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

        return {'id': entry.id,
                'trial': entry.trial,
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}


# Buy Form -> Database mapping
BUY_F2DB_FIELDS = {'fname-yui_3_10_1_1_1389902554996_14617':'firstname',
                   'lname-yui_3_10_1_1_1389902554996_14617':'lastname',
                   'text-yui_3_17_2_1_1426969180342_32971-field':'key',
                   'email-yui_3_10_1_1_1389902554996_14932-field': 'email',
                   'text-yui_3_10_1_1_1389902554996_16499-field': 'website',
                   'areacode-yui_3_17_2_1_1426969180342_43961': 'phone1',
                   'prefix-yui_3_17_2_1_1426969180342_43961': 'phone2',
                   'line-yui_3_17_2_1_1426969180342_43961': 'phone3',
                   'text-yui_3_17_2_1_1428080829349_25557-field': 'promo_code'}

# Buy Database -> Form mapping
BUY_DB2F_FIELDS = {v: k for k, v in BUY_F2DB_FIELDS.items()}

# Buy fields to fill in on a GET request
BUY_GET_FIELDS = ['firstname', 'lastname', 'key', 'email',
                  'website', 'phone', 'promo_code']

class Buy2RequestApplication(GenericWSGIApplication):
    """ Class that Handles get/post methods for the palette buy url
    """
    REDIRECT_URL = 'http://www.palette-software.com/subscribe-thank-you'

    def translate_POST(self, req, entry):
        # pylint: disable=invalid-name
        fname = req.POST.getall('fname')
        lname = req.POST.getall('lname')
        entry.firstname = fname[0]
        entry.lastname = lname[0]
        entry.billing_fn = fname[1]
        entry.billing_ln = lname[1]
        entry.email = req.POST['email']
        entry.website = req.POST['text-yui_3_10_1_1_1389902554996_16499-field']
        areacode = req.POST['areacode-yui_3_17_2_1_1426969180342_43961']
        prefix = req.POST['prefix-yui_3_17_2_1_1426969180342_43961']
        line = req.POST['line-yui_3_17_2_1_1426969180342_43961']
        entry.phone = areacode + '-' + prefix + '-' + line
        entry.billing_address_line1 = req.POST['address']
        entry.billing_address_line2 = req.POST['address2']
        entry.billing_city = req.POST['city']
        entry.billing_state = req.POST['state']
        entry.billing_zip = req.POST['zipcode']
        entry.billing_country = req.POST['country']
        coupon = req.POST['text-yui_3_17_2_1_1428080829349_25557-field']
        entry.promo_code = coupon

    def service_GET(self, req):
        """ Handle get request which looks up the key and redirects to a
            URL to buy with the info pre-populated on the form
            NOTE: never fail - always redirect to the buy page.
        """
        buy_url = System.get_by_key('BUY-URL')

        key = req.params_get('key')
        location = buy_url + '?' + BUY_DB2F_FIELDS['key'] + '=' + key

        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Buy request key not found:' + key)
            raise exc.HTTPTemporaryRedirect(location=location)

        logger.info('Processing Buy get request info for ' + key)

        data = {}
        for field in BUY_GET_FIELDS:
            if field == 'phone':
                if not entry.phone:
                    continue
                tokens = entry.phone.split('-')
                if len(tokens) == 4:
                    tokens.pop(0) # ignore country if present
                elif len(tokens) != 3:
                    logger.error('Invalid phone # found, key: ' + key)
                    continue
                data[BUY_DB2F_FIELDS['phone1']] = tokens.pop(0)
                data[BUY_DB2F_FIELDS['phone2']] = tokens.pop(0)
                data[BUY_DB2F_FIELDS['phone3']] = tokens.pop(0)
            else:
                data[BUY_DB2F_FIELDS[field]] = getattr(entry, field)

        location = buy_url + dict_to_qs(data)
        raise exc.HTTPTemporaryRedirect(location=location)

    @required_parameters('stripeToken')
    def service_POST(self, req):
        """ Handle a Buy Request
        """
        # key name and id are the same.
        key = req.params_get(BUY_DB2F_FIELDS['key'])
        entry = License.get_by_key(key)
        if entry is None:
            msg = "Buy request POST failed for '{1}' : {2}"\
                .format(key, str(req.POST))
            logger.error(msg)
            SlackAPI.notify(msg)
            # FIXME: re-route to a custom error page saying contact us.
            raise exc.HTTPNotFound()

        logger.info('Processing Buy Post request for ' + key)

        try:
            self.translate_POST(req, entry)
        except StandardError, ex:
            logger.error(key + ': ' + str(ex))
            raise exc.HTTPBadRequest()

        # first we charge them...
        token = req.POST['stripeToken']
        if entry.promo_code:
            customer = stripe.Customer.create(source=token,
                                              plan='MONTHLY',
                                              coupon=entry.promo_code,
                                              email=entry.email)
        else:
            customer = stripe.Customer.create(source=token,
                                              plan='MONTHLY',
                                              email=entry.email)
        entry.stripeid = customer.id

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
                      System.get_by_key('SENDWITHUS-CLOSED-WON-ID'),
                      'hello@palette-software.com',
                      entry.email,
                      populate_email_data(entry))

        SendwithusAPI.send_message(
                      System.get_by_key('SENDWITHUS-BUY-NOTIFICATION-ID'),
                      'licensing@palette-software.com',
                      'hello@palette-software.com',
                      populate_buy_email_data(entry))

        try:
            # This should only fail in testing, where there is no op.
            opportunity_name = SalesforceAPI.get_opportunity_name(entry)
        except StandardError:
            opportunity_name = 'UNKNOWN'

        SlackAPI.notify('Buy request Opportunity: {0} ({1}) - Type: {2}'\
                        .format(opportunity_name,
                                entry.email,
                                entry.hosting_type))

        logger.info('Buy request succeeded for {0}'.format(key))

        # use 302 here so that the browswer redirects with a GET request.
        return exc.HTTPFound(location=self.REDIRECT_URL)


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
# license verify by the conductor
router.add_route(r'/license\Z', LicenseApplication())
# support application requst
router.add_route(r'/support\Z', SupportApplication())
# UX redirects for expiration
router.add_route(r'/trial-expired\Z', Buy2RequestApplication())
router.add_route(r'/license-expired\Z', Buy2RequestApplication())
# GET redirects for the BUY button and POST handler
router.add_route(r'/buy\Z', Buy2RequestApplication())

# submit (POST) handler for the website /trial form.
router.add_route(r'/api/trial\Z', TrialRequestApplication())
# called when the initial setup page is completed.
router.add_route(r'/api/trial-start\Z', TrialStartApplication())

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
