import logging
import config

from system import System
from util import str2bool
from mailchimp import Mailchimp, ListAlreadySubscribedError

logger = logging.getLogger('licensing')

class MailchimpAPI():
    """ A wrapper class for the Mailchimp API
    """

    @classmethod
    def subscribe_user(cls, mailid, data):
        """ Subscribe a user to a given mailchimp list
        """
        chimp = Mailchimp(System.get_by_key('mailchimp_apikey'), \
                          debug=str2bool(System.get_by_key('mailchimp_debug')))
        email = {'email': data.email}
        merge_vars = {'FNAME':data.firstname, 'LNAME':data.lastname, \
                      'LICENSE': data.key}
        try:
            chimp.lists.subscribe(mailid, email, merge_vars,
                           double_optin=False, send_welcome=False)
        except ListAlreadySubscribedError:
            logger.info(' Mailchimp User {0} already subscribed'.format(email))

    @classmethod
    def unsubscribe_user(cls, mailid, data):
        """ Unsubscribe a user from the given list
        """
        pass
