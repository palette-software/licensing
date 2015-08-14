import logging
import uuid
from datetime import datetime
from webob import exc

from akiri.framework.sqlalchemy import get_session
from akiri.framework.util import required_parameters

from application import BaseApp
from contact import Email
from licensing import License
from product import Product
from register import redirect_verify
from stage import Stage
from system import System
from utils import get_netloc, domain_only, hostname_only, to_localtime
from utils import redirect_to_sqs, time_from_today

from boto_api import BotoAPI
from ansible_api import AnsibleAPI
from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI

# These are the literal plan names on Squarespace/start-trial
PALETTE_PRO = 'Palette Pro'
PALETTE_ENT = 'Palette Enterprise'

logger = logging.getLogger('licensing')

# FIXME: locking + database transaction so that add() doesn't blow up...
def unique_name(name):
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

def default_expiration():
    days = int(System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS'))
    return time_from_today(days=days)

def generate_license(sf, contact, product,
                     name=None, stage_key=None, expiration=None,
                     send_email=True, slack=True):
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    email = contact[SalesforceAPI.CONTACT_EMAIL_BASE]
    org = get_netloc(domain_only(email)).lower()

    if name is None:
        name = unique_name(hostname_only(org))
    if stage_key is None:
        stage_key = 'STAGE-TRIAL-REQUESTED'
    stage = Stage.get_by_key(stage_key)
    if expiration is None:
        expiration = default_expiration()

    logger.info('New trial request for %s', contact['Email'])
    entry = License()
    entry.key = str(uuid.uuid4())
    entry.name = name
    entry.email = email
    entry.expiration_time = expiration
    entry.stageid = stage.id

    entry.organization = org
    entry.website = org

    # FIXME: remove
    logger.info('{0} {1} {2}'.format(entry.organization,
                                     entry.subdomain,
                                     entry.name))

    entry.registration_start_time = datetime.utcnow()
    entry.productid = Product.get_by_key(Product.PRO_KEY).id
    if product.key == Product.PRO_KEY:
        entry.subdomain = entry.name
        entry.aws_zone = BotoAPI.get_region_by_name(entry.aws_zone)
        entry.access_key, entry.secret_key = BotoAPI.create_s3(entry)

    # FIXME
    session = get_session()
    session.add(entry)
    session.commit()

    # create the opportunity
    opportunity_name = SalesforceAPI.license_to_oppname(contact['Name'], entry)
    opp_id = SalesforceAPI.create_opportunity(sf, opportunity_name,
                                              contact['AccountId'], entry,
                                              slack=slack)

    # Add a primary,'Evaluator' contact role to the opportunity for 'contact'
    SalesforceAPI.add_contact_role(sf, opp_id, contact['Id'])

    # subscribe the user to the trial list
    email_data = SendwithusAPI.gather_email_data(contact, entry)
    if product.key == Product.PRO_KEY:
        if send_email:
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-REQUESTED-PRO-ID',
                                         'hello@palette-software.com',
                                         entry.email,
                                         email_data)

    else:
        if send_email:
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-REQUESTED-ENT-ID',
                                         'hello@palette-software.com',
                                         entry.email,
                                         email_data)
            SendwithusAPI\
                .send_message('SENDWITHUS-TRIAL-REQUESTED-ENT-INTERNAL-ID',
                              'licensing@palette-software.com',
                              'support@palette-software.com',
                              email_data)

    sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
    expiration_time = to_localtime(entry.expiration_time).strftime("%x")
    if slack:
        SlackAPI.info('*{0}* Opportunity: '
                      '{1} ({2}) - Type: {3} {4} Expiration {5}'.format(
                          stage.name, opportunity_name, contact['Email'],
                          product.name, sf_url, expiration_time))

    return entry


class TrialRequestApplication(BaseApp):
    """
    This application is called by Squarespace when a user
    fills out the start-trial form after verifying their email.
    """
    PALETTE_PRO = PALETTE_PRO
    PALETTE_ENT = PALETTE_ENT

    # pylint: disable=too-many-statements
    @required_parameters('fname', 'lname', 'email', 'plan', 'SQF_KEY')
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        # pylint: disable=too-many-locals
        fname = req.params['fname']
        lname = req.params['lname']
        email = Email(req.params['email'])
        plan = req.params['plan']

        sf = SalesforceAPI.connect()

        key = req.params['SQF_KEY']
        # SQF_KEY is a hidden field in the trial page
        # if no key then the no registeration was done and
        # the trial form was filled-in to start
        if not key:
            contact = SalesforceAPI.get_contact_by_email(sf, email.base)
            if contact is None:
                contact_id = SalesforceAPI.create_contact(sf, fname,
                                                          lname, email)
                contact = sf.Contact.get(contact_id)
            if not contact[SalesforceAPI.CONTACT_VERFIED]:
                logger.warn('Redirect/verify from start-trial: ' + str(email))
                return redirect_verify(fname, lname, email)
        else:
            contact = SalesforceAPI.get_contact_by_email(sf, key)

        # Here we have a verified contact.

        if plan == PALETTE_PRO:
            product = Product.get_by_key(Product.PRO_KEY)
            redirect_url = System.get_by_key('TRIAL-REQUEST-REDIRECT-PRO-URL')
        elif plan == PALETTE_ENT:
            product = Product.get_by_key(Product.ENT_KEY)
            redirect_url = System.get_by_key('TRIAL-REQUEST-REDIRECT-ENT-URL')
        # else?

        entry = License.get_by_email(email.base)
        if entry:
            SlackAPI.warning('Existing trial for ' + email.base)
            return redirect_to_sqs(redirect_url)

        entry = generate_license(sf, contact, product)
        if plan == PALETTE_PRO:
            AnsibleAPI.launch_instance(entry, contact,
                                       'PALETTECLOUD-LAUNCH-SUCCESS-ID',
                                       'PALETTECLOUD-LAUNCH-FAIL-ID')

        return redirect_to_sqs(redirect_url)


class TrialStartApplication(BaseApp):
    """
    This application is called when the user presses 'Save Settings' on the
    initial setup page.
    The POST request comes from Palette Server (not the website)
    """
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

        # FIXME
        session = get_session()

        # FIXME: *only* do this if in the correct stage (otherwise free trials!)
        if entry.stageid == Stage.get_by_key('STAGE-CLOSED-WON').id:
            # if already set to closed won just update time and notify
            if entry.license_start_time is None:
                entry.license_start_time = datetime.utcnow()
            entry.contact_time = datetime.utcnow()

            session.commit()

            logger.info('License Start for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time))

            # update the opportunity
            opp_id = SalesforceAPI.update_opportunity(entry)

            # FIXME
            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
            SlackAPI.notify('*{0}* '
                            'Key: {1}, Name: {2} ({3}), Type: {4} {5} '\
                            'Expiration {7}' \
                    .format(entry.stage.name, entry.key, entry.name,
                            entry.email, entry.product.name, sf_url,
                            to_localtime(entry.expiration_time).strftime("%x")))

        elif entry.stageid == Stage.get_by_key('STAGE-TRIAL-REQUESTED').id:
            logger.info('Starting Trial for key {0}'.format(key))

            # start the trial
            stage = Stage.get_by_key('STAGE-TRIAL-STARTED')
            entry.stageid = stage.id
            entry.expiration_time = time_from_today(\
                days=int(System.get_by_key('TRIAL-REG-EXPIRATION-DAYS')))
            entry.trial_start_time = datetime.utcnow()
            entry.contact_time = entry.trial_start_time

            # FIXME
            session.commit()

            logger.info('Trial Start for key {0} success. Expiration {1}'\
                        .format(key, entry.expiration_time))

            # update the opportunity
            opp_id = SalesforceAPI.update_opportunity(entry)

            sf = SalesforceAPI.connect()
            contact = SalesforceAPI.get_contact_by_email(sf, entry.email)

            # subscribe the user to the trial workflow if not already
            email_data = SendwithusAPI.gather_email_data(contact, entry)
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-STARTED-ID',
                                         'hello@palette-software.com',
                                         contact['Email'], email_data)

            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
            SlackAPI.notify('*{0}* '
                            'Key: {1}, Name: {2} ({3}), Type: {4} {5} '\
                            'Expiration: {6}' \
                    .format(stage.name, entry.key, entry.name, entry.email,
                            entry.product.name, sf_url,
                            to_localtime(entry.expiration_time).strftime("%x")))
        else:
            logger.info('Licensing ping received for key {0}'.format(key))
            # just update the last contact time
            entry.contact_time = datetime.utcnow()
            session.commit()

        return {'id': entry.id,
                'trial': entry.istrial(),
                'stage': entry.stage.name,
                'expiration-time': str(entry.expiration_time)}
