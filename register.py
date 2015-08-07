# The module handles the registration and verification of new users.
import logging
import uuid
from datetime import datetime
from webob import exc

from akiri.framework import GenericWSGIApplication
from akiri.framework.sqlalchemy import get_session # FIXME
from akiri.framework.util import required_parameters

from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI

from licensing import License
from stage import Stage
from system import System

from utils import get_netloc, hostname_only, domain_only, to_localtime, \
    dict_to_qs, time_from_today

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

class RegisterApplication(GenericWSGIApplication):
    """Create a new but unverified user in the database."""

    @required_parameters('fname', 'lname', 'email')
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
            entry.firstname = req.params['fname']
            entry.lastname = req.params['lname']
            entry.email = req.params['email']

            logger.info('New register request for %s %s %s',
                        entry.firstname, entry.lastname, entry.email)

            entry.key = str(uuid.uuid4())
            entry.stageid = Stage.get_by_key('STAGE-REGISTERED-UNVERIFIED').id
            entry.registration_start_time = datetime.utcnow()
            entry.expiration_time = time_from_today(hours=24)
            entry.organization = get_netloc(domain_only(entry.email)).lower()
            entry.website = entry.organization
            entry.subdomain = unique_name(hostname_only(entry.organization))
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
    """
    This application is called when the user verifies their email address.
    The verification is done by the user clicking on a link in an email
    that was sent to them during registration.
    """
    def service_GET(self, req):
        """Handle a Registration Validation of a new potential trial user
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
