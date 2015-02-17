import logging
from mailchimp import Mailchimp, ListAlreadySubscribedError

from config import get_config, get_config_bool

logger = logging.getLogger('licensing')

class MailchimpAPI():
    """ A wrapper class for the Mailchimp API
    """

    @classmethod
    def subscribe_user(cls, mailid, data):
        """ Subscribe a user to a given mailchimp list
        """
        chimp = Mailchimp(get_config('mailchimp_apikey'), \
                          debug=get_config_bool('mailchimp_debug'))
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
