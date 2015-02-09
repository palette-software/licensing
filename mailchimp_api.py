from mailchimp import Mailchimp, ListAlreadySubscribedError

import config

class MailchimpAPI():
    """
    """

    @classmethod
    def subscribe_user(cls, title, data):
        """ Subscribe a user to a given mailchimp list
        """
        def find_id(title):
            """ Find the id for a mailchip list using the list name
            """
            chimp = Mailchimp(config.MAILCHIMP_APIKEY, 
                              debug = config.MAILCHIMP_DEBUG)
            lists = chimp.lists.list()['data']
            for i in lists:
                if i['name'] == title:
                    return i['id']
            return None

        mailid = find_id(title)
        if mailid is None:
            # Fixme log an error
            return

        chimp = Mailchimp(config.MAILCHIMP_APIKEY, config.MAILCHIMP_DEBUG)
        email = {'email': data['email']}
        merge_vars = {'FNAME':data['fn'], 'LNAME':data['ln'], 'LICENSE': data['key']}
        try:
            chimp.lists.subscribe(mailid, email, merge_vars,
                           double_optin=False, send_welcome=False)
        except ListAlreadySubscribedError:
            print 'User {0} already subscribed'.format(email)

