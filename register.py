# The module handles the registration and verification of new users.
import logging
import urllib
from webob import exc

from akiri.framework.util import required_parameters

from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI

from application import BaseApp
from contact import Email
from system import System

from utils import dict_to_qs

logger = logging.getLogger('licensing')

def redirect_verify(fname, lname, email):
    """
    Send an email to an unverified user and respond to the current HTTP
    request with a redirect to the 'Thank your for registering' SQS page.
    The email parameter must be an instance of contact.Email.
    """
    # send the user an email to allow them to verify their email address
    register_url = System.get_by_key('REGISTER-VERIFY-URL')
    redirect_url = '{0}?value={1}'.format(register_url,
                                          urllib.quote(email.base))
    email_data = {'firstname':fname, 'lastname':lname, 'url':redirect_url}
    SendwithusAPI.send_message('SENDWITHUS-REGISTERED-UNVERIFIED-ID',
                               'hello@palette-software.com',
                               email.full, email_data)

    # use 302 here so that the browser redirects with a GET request.
    url = System.get_by_key('REGISTER-REDIRECT-URL')
    return exc.HTTPFound(location=url)


class RegisterApplication(BaseApp):
    """Create a new but unverified user in the database."""

    @required_parameters('fname', 'lname', 'email')
    def service_POST(self, req):
        """ Handle a Registration of a new potential trial user
        """
        sf = SalesforceAPI.connect()

        fname = req.params['fname']
        lname = req.params['lname']
        email = Email(req.params['email'])

        contact_id = SalesforceAPI.get_contact_id(sf, email.base)
        if contact_id is None:
            SalesforceAPI.create_contact(sf,
                                         fname, lname,
                                         email, verified=False)
        else:
            SlackAPI.warning("Existing contact '{0}'".format(email.full))

        return redirect_verify(fname, lname, email)


class VerifyApplication(BaseApp):
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
            SlackAPI.error('Unverified email not found: ' + value)
            raise exc.HTTPNotFound()

        verified = contact[SalesforceAPI.CONTACT_VERFIED]
        if verified:
            SlackAPI.warning('Contact already verfied: ' + email)
        else:
            data = {SalesforceAPI.CONTACT_VERFIED: True}
            sf.Contact.update(contact['Id'], data)
            SlackAPI.info('*Contact Verified* ' + email)

        base_email = contact[SalesforceAPI.CONTACT_EMAIL_BASE]
        data = {'fname': contact['FirstName'],
                'lname': contact['LastName'],
                'email': email,
                'key': base_email}

        url = System.get_by_key('VERIFY-REDIRECT-URL')
        location = url + dict_to_qs(data)
        # use 302 here so that the browswer redirects with a GET request.
        return exc.HTTPFound(location=location)
