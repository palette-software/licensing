# The module handles the registration and verification of new users.
import logging
import urllib
from webob import exc

from akiri.framework import GenericWSGIApplication
from akiri.framework.util import required_parameters

from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI

from contact import Email

from licensing import License
from system import System

from utils import get_netloc, domain_only, dict_to_qs

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

# FIXME
def notify_info(msg):
    logger.info(msg)
    SlackAPI.notify(msg)

def notify_warning(msg):
    logger.error(msg)
    SlackAPI.notify('*WARNING* ' + msg)

def notify_error(msg):
    logger.error(msg)
    SlackAPI.notify('*ERROR* ' + msg)

class RegisterApplication(GenericWSGIApplication):
    """Create a new but unverified user in the database."""

    @required_parameters('fname', 'lname', 'email')
    def service_POST(self, req):
        """ Handle a Registration of a new potential trial user
        """
        sf = SalesforceAPI.connect()

        fname = req.params['fname']
        lname = req.params['lname']
        email = Email(req.params['email'])
        website = get_netloc(domain_only(email.base)).lower()

        # accounts are named by website
        account_id = SalesforceAPI.get_account_id(sf, website)
        if account_id is None:
            account = sf.Account.create({'Name': website,
                                         'Website': website})
            account_id = account['id']
            notify_info("Created new account '" + website + "'")

        contact_id = SalesforceAPI.get_contact_id(sf, email.base)
        if contact_id is None:
            data = {'AccountId': account_id,
                    'Firstname': fname, 'Lastname': lname,
                    'Email': email.full, 'Base_Email__c': email.base}
            sf.Contact.create(data)

            contact_name = '{0} {1} <{2}>'.format(fname, lname, email.base)
            notify_info("*New Contact* (unverified): '" + contact_name + "'")

        # send the user an email to allow them to verify their email address
        redirect_url = System.get_by_key('REGISTER-VERIFY-URL')
        url = '{0}?value={1}'.format(redirect_url, urllib.quote(email.base))
        SendwithusAPI.send_message('SENDWITHUS-REGISTERED-UNVERIFIED-ID',
                                   'hello@palette-software.com',
                                   email.full,
                                   {'firstname':fname,
                                    'lastname':lname,
                                    'url':url
                                   })

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
        if 'value' not in req.params:
            raise exc.HTTPBadRequest()

        # 'value' is the (encoded) contact base email
        value = req.params['value']
        email = urllib.unquote(value)

        sf = SalesforceAPI.connect()
        contact = SalesforceAPI.get_contact_by_email(sf, email)

        if contact is None:
            notify_error('Unverified email not found: ' + value)
            raise exc.HTTPNotFound()

        verified = contact[SalesforceAPI.CONTACT_VERFIED]
        if verified:
            notify_warning('Contact already verfied: ' + email)
        else:
            data = {SalesforceAPI.CONTACT_VERFIED: True}
            sf.Contact.update(contact['Id'], data)
            notify_info('*Contact Verified* ' + email)

        base_email = contact[SalesforceAPI.CONTACT_EMAIL_BASE]
        data = {'fname': contact['FirstName'],
                'lname': contact['LastName'],
                'email': email,
                'key': base_email}

        url = System.get_by_key('VERIFY-REDIRECT-URL')
        location = url + dict_to_qs(data)
        # use 302 here so that the browswer redirects with a GET request.
        return exc.HTTPFound(location=location)
