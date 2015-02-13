from mailchimp import Mailchimp, ListAlreadySubscribedError

import config

class MailchimpAPI():
    """
    """

    @classmethod
    def subscribe_user(cls, mailid, data):
        """ Subscribe a user to a given mailchimp list
        """
        chimp = Mailchimp(config.MAILCHIMP_APIKEY, config.MAILCHIMP_DEBUG)
        email = {'email': data.email}
        merge_vars = {'FNAME':data.firstname, 'LNAME':data.lastname, \
                      'LICENSE': data.key}
        try:
            chimp.lists.subscribe(mailid, email, merge_vars,
                           double_optin=False, send_welcome=False)
        except ListAlreadySubscribedError:
            print 'User {0} already subscribed'.format(email)

