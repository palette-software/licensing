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
from stage import Stage
from system import System
from utils import get_netloc, domain_only, hostname_only, to_localtime
from utils import redirect_to_sqs, time_from_today

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

def default_opportunity_name(full_name, org, utcts):
    """ Returns the standard name for an opportunity"""
    timestamp = to_localtime(utcts).strftime('%x %X')
    return org + ' ' + full_name + ' ' + timestamp

def default_expiration():
    expiration_days = System.get_by_key('TRIAL-REQ-EXPIRATION-DAYS')
    if expiration_days:
        days = int(expiration_days)
    else:
        days = 14
    return time_from_today(days=days)

def generate_license(contact, product,
                     name=None, stage_key=None, expiration=None,
                     send_email=True, slack=True):
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    email = str(contact['Email'])

    # FIXME
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

    entry.registration_start_time = datetime.utcnow()
    entry.productid = Product.get_by_key(Product.PRO_KEY).id

    # FIXME
    session = get_session()
    session.add(entry)
    session.commit()

    # create the opportunity
    opportunity_name = default_opportunity_name(contact['Name'], org,
                                                entry.registration_start_time)

    expiration_time = to_localtime(entry.expiration_time).strftime("%x")
    if slack:
        msg = '*{0}* {1} *{2}* : {3}, Expires at {4}'.\
              format(stage.name, product.name,
                     entry.name, entry.key, expiration_time)
        SlackAPI.info(msg)

    return entry


class TrialRequestApplication(BaseApp):
    """
    This application is called by Squarespace when a user
    fills out the start-trial form after verifying their email.
    """
    PALETTE_PRO = PALETTE_PRO
    PALETTE_ENT = PALETTE_ENT

    # pylint: disable=too-many-statements
    # @required_parameters('fname', 'lname', 'email', 'plan')
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        # pylint: disable=too-many-locals
	redirect_url = System.get_by_key('TRIAL-REQUEST-REDIRECT-ENT-URL')
	try:
            fname = req.params['fname']
            lname = req.params['lname']
            email = Email(req.params['email'])
            plan = req.params['plan']
	except:
	    return redirect_to_sqs(redirect_url)

        if plan == PALETTE_PRO:
            product = Product.get_by_key(Product.PRO_KEY)
            redirect_url = System.get_by_key('TRIAL-REQUEST-REDIRECT-PRO-URL')
        elif plan == PALETTE_ENT:
            product = Product.get_by_key(Product.ENT_KEY)
            redirect_url = System.get_by_key('TRIAL-REQUEST-REDIRECT-ENT-URL')
	else:
	    return redirect_to_sqs(redirect_url)
        # else?

        entry = License.get_by_email(email.base)
        if entry:
            SlackAPI.warning('Existing trial for ' + email.base)
            return redirect_to_sqs(redirect_url)


	contact = {}
	contact['Email'] = email.base
	contact['Name'] = fname + ' ' + lname
	contact['FirstName'] = fname
	contact['LastName'] = lname
        entry = generate_license(contact, product)

        return redirect_to_sqs(redirect_url)


class TrialStartApplication(BaseApp):
    """
    This application is called when the user presses 'Save Settings' on the
    initial setup page.
    The POST request comes from Palette Server (not the website)
    """
    @required_parameters('license-key')
    def service_POST(self, req):
        """ Handle a Trial start
        """
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Invalid trial start key: ' + key)
            raise exc.HTTPNotFound()

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

        else:
            logger.info('Licensing ping received for key {0}'.format(key))
            # just update the last contact time
            entry.contact_time = datetime.utcnow()
            session.commit()

        return {'id': entry.id,
                'trial': entry.istrial(),
                'stage': entry.stage.name,
                'name': entry.name,
                'expiration-time': str(entry.expiration_time)}
