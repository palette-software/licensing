import sendwithus

import logging
from system import System

logger = logging.getLogger('licensing')

# pylint: disable=too-many-arguments

class SendwithusAPI(object):

    @classmethod
    def subscribe_user(cls, swu_id, from_address, to_address, data):
        mailid = System.get_by_key(swu_id)
        # if the given message id is disabled continue
        if mailid is None or mailid.lower() == "none":
            logger.info('Not sending message for %s', swu_id)
            return

        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        response = api.start_on_drip_campaign(
            mailid,
            {'address':to_address},
            email_data=data,
            sender={'address':from_address})
        if response.status_code != 200:
            logger.error('Error subscribing user %s to %s: %s',
                          to_address, mailid, response.content)

    @classmethod
    def send_message(cls, swu_id, from_address, to_address, data, files=None):
        mailid = System.get_by_key(swu_id)
        # if the given message id is disabled continue
        if mailid is None or mailid.lower() == "none":
            logger.info('Not sending message for %s', swu_id)
            return

        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        response = api.send(email_id=mailid,
                            email_data=data,
                            recipient={'address':to_address},
                            sender={'address':from_address},
                            files=files)
        if response.status_code != 200:
            logger.error('Error sending message %s to user %s: %s',
                         mailid, to_address, response.content)

    @classmethod
    def gather_email_data(cls, contact, entry):
        """Generate a dict from a SF contact and a license instance"""
        email_data = {'license': entry.key,
                      'firstname': contact['FirstName'],
                      'lastname': contact['LastName'],
                      'email': contact['Email'], # entry.email is the base
                      'organization': entry.organization,
                      'hosting_type': entry.hosting_type,
                      'promo_code': entry.promo_code,
                      'subdomain': entry.subdomain,
                      'access_key': entry.access_key,
                      'secret_key': entry.secret_key}
        return email_data
