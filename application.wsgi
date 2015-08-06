#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

import stripe
# stripe.api_key = 'sk_test_ynEoVFrJuhuZ2cVmhCu0ePU4'
stripe.api_key = 'sk_live_VQnPZ5WlUY0hgbYv5KsGUM80'

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

from subscribe import SubscribeApplication

from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI
from ansible_api import AnsibleAPI
from boto_api import BotoAPI
from utils import get_netloc, hostname_only, domain_only, \
    to_localtime, dict_to_qs

# pylint: disable=unused-import
from billing import Billing
from stage import Stage
from licensing import License
from support import Support
from system import System
from product import Product
from server_info import ServerInfo

# currently is set to 'trust' for the loopback interface so use the old pw.
DATABASE = 'postgresql://palette:palpass@localhost/licensedb'

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
                  'email':entry.email,
                  'organization':entry.organization,
                  'hosting_type':entry.hosting_type,
                  'promo_code':entry.promo_code,
                  'subdomain':entry.subdomain,
                  'access_key':entry.access_key,
                  'secret_key':entry.secret_key}
    return email_data

def populate_buy_email_data(entry):
    """ creates a dict that contains the fields to put passed to buy emails
    """
    data = {'firstname':entry.firstname,
            'lastname':entry.lastname,
            'email':entry.email,
            'phone':entry.phone,
            'org':entry.organization,
            'hosting_type':entry.hosting_type}

    if entry.billing:
        data['billing_address_line1'] = entry.billing.address_line1
        data['billing_address_line2'] = entry.billing.address_line2
        data['billing_city'] = entry.billing.city
        data['billing_state'] = entry.billing.state
        data['billing_zip'] = entry.billing.zipcode
        data['billing_country'] = entry.billing.country
    return data

def get_plan_quantity_amount(entry):
    """ Return the plan and quantity and amount  based on the product, type
        Tableau License
    """
    plan = None
    amount = None

    if entry.productid == Product.get_by_key('PALETTE-PRO').id:
        # return palette pro cost which has a fixed cost
        plan = System.get_by_key('PALETTE-PRO-PLAN')
        quantity = 1
        amount = int(System.get_by_key('PALETTE-PRO-COST'))
    elif entry.productid == Product.get_by_key('PALETTE-ENT').id:
        # return palette enterprise cost which depends on license type
        quantity = entry.n
        if entry.type == 'Named-user':
            plan = System.get_by_key('PALETTE-ENT-NAMED-USER-PLAN')
            amount = int(System.get_by_key('PALETTE-ENT-NAMED-USER-COST')) \
                         * quantity
        elif entry.type == 'Core':
            plan = System.get_by_key('PALETTE-ENT-CORE-PLAN')
            amount = int(System.get_by_key('PALETTE-ENT-CORE-COST')) \
                         * quantity
    if plan is None or amount is None:
        # if product id, entry type or n is not set just return the cost
        # for for 1 named user
        quantity = 1
        plan = System.get_by_key('PALETTE-ENT-NAMED-USER-PLAN')
        amount = int(System.get_by_key('PALETTE-ENT-NAMED-USER-COST')) \
                     * quantity
    return plan, quantity, amount

class SupportApplication(GenericWSGIApplication):

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

class HomePage(GenericWSGIApplication):

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # pylint: disable=line-too-long
        return "<html>\n" + \
               "<img src='http://static1.squarespace.com/static/52f6835ce4b09d0c2500656c/t/551201ebe4b0b870a8cbc323/1437579772393/?format=1500w' width='800'>" + \
               "\n</html>\n"

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

REGISTER_FIELDS = {
        'fname':'firstname', 'lname':'lastname',
        'email':'email',
}
class RegisterApplication(GenericWSGIApplication):
    @required_parameters(*REGISTER_FIELDS.keys())
    def service_POST(self, req):
        """ Handle a Registration of a new potential trial user
        """
        session = get_session()
        entry = License.get_by_email(req.params['email'])
        if entry is not None:
            logger.info('Re-register request for %s %s %s',
                        entry.firstname, entry.lastname, entry.email)

            entry.registration_start_time = datetime.utcnow()
            entry.expiration_time = time_from_today(hours=24)
            session.commit()
        else:
            entry = License()
            translate_values(req.params, entry, REGISTER_FIELDS)
            logger.info('New register request for %s %s %s',
                        entry.firstname, entry.lastname, entry.email)

            entry.key = str(uuid.uuid4())
            entry.stageid = Stage.get_by_key('STAGE-REGISTERED-UNVERIFIED').id
            entry.registration_start_time = datetime.utcnow()
            entry.expiration_time = time_from_today(hours=24)
            entry.organization = get_netloc(domain_only(entry.email)).lower()
            entry.website = entry.organization
            entry.subdomain = get_unique_name(hostname_only(entry.organization))
            entry.name = entry.subdomain
            entry.salesforceid = SalesforceAPI.new_opportunity(entry)
            session.add(entry)
            session.commit()

            # notify slack
            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(),
                                      entry.salesforceid)
            SlackAPI.notify('*{0}* Opportunity: '
                    '{1} ({2}) {3} Expiration {4}'.format(
                    Stage.get_stage_name(entry.stageid),
                    SalesforceAPI.get_opportunity_name(entry),
                    entry.email,
                    sf_url,
                    to_localtime(entry.expiration_time).strftime("%x")))

        # send the user an email to allow them to verify their email address
        redirect_url = System.get_by_key('REGISTER-VERIFY-URL')
        url = '{0}?key={1}'.format(redirect_url, entry.key)
        SendwithusAPI.send_message('SENDWITHUS-REGISTERED-UNVERIFIED-ID',
                                   'hello@palette-software.com',
                                   entry.email,
                                   {'firstname':entry.firstname,
                                    'lastname':entry.lastname,
                                    'key':entry.key,
                                    'url':url
                                   })

        logger.info('Register unvalidated success for %s', entry.email)

        # use 302 here so that the browswer redirects with a GET request.
        url = System.get_by_key('REGISTER-REDIRECT-URL')
        return exc.HTTPFound(location=url)

class VerifyApplication(GenericWSGIApplication):
    def service_GET(self, req):
        """ Handle a Registration Validation of a new potential trial user
        """
        entry = License.get_by_key(req.params['key'])
        if entry is None:
            raise exc.HTTPNotFound()

        session = get_session()
        entry.stageid = Stage.get_by_key('STAGE-VERIFIED').id
        entry.expiration_time = time_from_today(months=1)
        session.commit()

        # update existing opportunity
        opp_id = SalesforceAPI.update_opportunity(entry)

        # notify slack
        sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
        SlackAPI.notify('*{0}* Opportunity: '
                '{1} ({2}) {3} Expiration {4}'.format(
                 Stage.get_stage_name(entry.stageid),
                SalesforceAPI.get_opportunity_name(entry),
                entry.email,
                sf_url,
                to_localtime(entry.expiration_time).strftime("%x")))

        logger.info('Register verified success for %s', entry.email)

        data = {'fname-yui_3_10_1_1_1389902554996_14617':entry.firstname,
                'lname-yui_3_10_1_1_1389902554996_14617':entry.lastname,
                'email-yui_3_10_1_1_1389902554996_14932-field':entry.email,
                'hidden-yui_3_17_2_1_1429117178321_54646':entry.key}

        url = System.get_by_key('VERIFY-REDIRECT-URL')
        location = url + dict_to_qs(data)
        # use 302 here so that the browswer redirects with a GET request.
        return exc.HTTPFound(location=location)

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

        logger.info('Updating license information for %s', key)

        entry.contact_time = datetime.utcnow()
        session = get_session()
        session.commit()

        keys = ['palette-version',
                'tableau-version', 'tableau-bitness', 'primary-os-version',
                'processor-type', 'processor-count', 'processor-bitness']

        details = {}
        for i in keys:
            if req.params.get(i) is not None:
                details[i] = req.params.get(i)
        ServerInfo.upsert(entry.id, details)
        SalesforceAPI.update_opportunity_details(entry, details)

        return {'id': entry.id,
                'trial': entry.istrial(),
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}


TRIAL_FIELDS = {
    'fname':'firstname', 'lname':'lastname',
    'email':'email',
    'radio-yui_3_17_2_1_1426521445942_51014-field':'hosting_type'
}

class TrialRequestApplication(GenericWSGIApplication):

    TRIAL_FIELDS = TRIAL_FIELDS
    PALETTE_PRO = 'Palette Pro'
    PALETTE_ENT = 'Palette Enterprise'

# pylint: disable=too-many-statements
    @required_parameters(*TRIAL_FIELDS.keys())
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        key = req.params['SQF_KEY']
        # sqf is a hidden field in the trial page
        # if no key then the no registeration was done and
        # the trial form was filled-in to start
        if len(key) == 0:
            entry = License()
            translate_values(req.params, entry, self.TRIAL_FIELDS)
            logger.info('New trial request for %s %s %s',
                        entry.firstname,
                        entry.lastname,
                        entry.email)
            entry.key = str(uuid.uuid4())
            entry.expiration_time = time_from_today(
                days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
            entry.stageid = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id
            entry.organization = get_netloc(domain_only(entry.email)).lower()
            entry.website = entry.organization
            entry.subdomain = get_unique_name(hostname_only(entry.organization))
            entry.name = entry.subdomain
            logger.info('{0} {1} {2}'.format(entry.organization,
                                                 entry.subdomain,
                                                 entry.name))

            entry.registration_start_time = datetime.utcnow()
            if entry.hosting_type == TrialRequestApplication.PALETTE_PRO:
                entry.productid = Product.get_by_key('PALETTE-PRO').id
                entry.aws_zone = BotoAPI.get_region_by_name(entry.aws_zone)
                entry.access_key, entry.secret_key = BotoAPI.create_s3(entry)
            else:
                entry.productid = Product.get_by_key('PALETTE-ENT').id

            session = get_session()
            session.add(entry)
            session.commit()

            # create or use an existing opportunity
            opp_id = SalesforceAPI.new_opportunity(entry)
        else:
            # if there was a key it means they registered before

            logger.info('Key is %s', key)
            entry = License.get_by_key(key)
            if entry is None:
                logger.error('Invalid license key: ' + key)
                raise exc.HTTPNotFound()

            translate_values(req.params, entry, self.TRIAL_FIELDS)
            logger.info('New registered trial request for %s %s %s',
                        entry.firstname,
                        entry.lastname,
                        entry.email)
            entry.expiration_time = time_from_today(
                days=int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')))
            entry.stageid = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id
            if entry.hosting_type == TrialRequestApplication.PALETTE_PRO:
                entry.productid = Product.get_by_key('PALETTE-PRO').id
                entry.aws_zone = BotoAPI.get_region_by_name(entry.aws_zone)
                entry.access_key, entry.secret_key = BotoAPI.create_s3(entry)
            else:
                entry.productid = Product.get_by_key('PALETTE-ENT').id

            session = get_session()
            session.commit()

            # update the sf opportunity
            opp_id = SalesforceAPI.update_opportunity(entry)

        # subscribe the user to the trial list
        if entry.hosting_type == TrialRequestApplication.PALETTE_PRO:
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-REQUESTED-PRO-ID',
                                         'hello@palette-software.com',
                                         entry.email,
                                         populate_email_data(entry))

            AnsibleAPI.launch_instance(entry,
                                       'PALETTECLOUD-LAUNCH-SUCCESS-ID',
                                       'PALETTECLOUD-LAUNCH-FAIL-ID')
            url = System.get_by_key('TRIAL-REQUEST-REDIRECT-PRO-URL')

        else:
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-REQUESTED-ENT-ID',
                                         'hello@palette-software.com',
                                         entry.email,
                                         populate_email_data(entry))
            SendwithusAPI\
               .send_message('SENDWITHUS-TRIAL-REQUESTED-ENT-INTERNAL-ID',
                             'licensing@palette-software.com',
                             'support@palette-software.com',
                             populate_email_data(entry))
            url = System.get_by_key('TRIAL-REQUEST-REDIRECT-ENT-URL')

        sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
        SlackAPI.notify('*{0}* Opportunity: '
                '{1} ({2}) - Type: {3} {4} Expiration {5}'.format(
                Stage.get_stage_name(entry.stageid),
                SalesforceAPI.get_opportunity_name(entry),
                entry.email,
                entry.hosting_type,
                sf_url,
                to_localtime(entry.expiration_time).strftime("%x")))

        logger.info('Trial request success for %s %s', entry.email, entry.key)

        # use 302 here so that the browswer redirects with a GET request.
        return exc.HTTPFound(location=url)


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
        SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-REGISTERED-ID',
                                     'hello@palette-software.com',
                                     entry.email,
                                     populate_email_data(entry))

        logger.info('Trial Registration for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

        return {'trial': entry.istrial(),
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
            logger.error('Invalid trial start key: ' + key)
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
        if entry.stageid == Stage.get_by_key('STAGE-CLOSED-WON').id:
            #if already set to closed won just update time and notify
            if entry.license_start_time is None:
                entry.license_start_time = datetime.utcnow()
            entry.contact_time = datetime.utcnow()

            session.commit()

            logger.info('License Start for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

            # update the opportunity
            opp_id = SalesforceAPI.update_opportunity(entry)

            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
            SlackAPI.notify('*{0}* '
                    'Key: {1}, Name: {2} ({3}), Org: {4}, Type: {5} {6} '\
                    'Expiration {7}' \
                    .format(Stage.get_stage_name(entry.stageid), entry.key,
                    entry.firstname + ' ' + entry.lastname, entry.email,
                    entry.organization, entry.hosting_type, sf_url,
                    to_localtime(entry.expiration_time).strftime("%x")))

        elif entry.stageid != Stage.get_by_key('STAGE-TRIAL-STARTED').id:
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
            opp_id = SalesforceAPI.update_opportunity(entry)
            # subscribe the user to the trial workflow if not already
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-STARTED-ID',
                                         'hello@palette-software.com',
                                         entry.email,
                                         populate_email_data(entry))

            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
            SlackAPI.notify('*{0}* '
                    'Key: {1}, Name: {2} ({3}), Org: {4}, Type: {5} {6} '\
                    'Expiration: {7}' \
                    .format(Stage.get_stage_name(entry.stageid), entry.key,
                    entry.firstname + ' ' + entry.lastname, entry.email,
                    entry.organization, entry.hosting_type, sf_url,
                    to_localtime(entry.expiration_time).strftime("%x")))
        else:
            logger.info('Licensing ping received for key {0}'.format(key))
            # just update the last contact time
            entry.contact_time = datetime.utcnow()
            session.commit()

        return {'id': entry.id,
                'trial': entry.istrial(),
                'stage': Stage.get_by_id(entry.stageid).name,
                'expiration-time': str(entry.expiration_time)}

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
# Home page
router.add_route(r'/\Z', HomePage())

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
