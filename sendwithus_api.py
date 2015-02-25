import sendwithus

import logging
from system import System

logger = logging.getLogger('licensing')

class SendwithusAPI(object):

    @classmethod
    def subscribe_user(cls, mailid, data):
        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        response = api.start_on_drip_campaign(
            mailid,
            {'address':data.email}, \
              email_data={'license':data.key,
                          'firstname':data.firstname,
                          'lastname':data.lastname,
                          'organization':data.organization,
                          'hosting_type':data.hosting_type,
                          'subdomain':data.subdomain},
            sender={'address': 'hello@palette-software.com'})
        if response.status_code != 200:
            logger.error('Error subscribing user %s to %s', data.email, mailid)

    @classmethod
    def send_message(cls, mailid, from_address, to_address):
        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        response = api.send(
            email_id=mailid,
            recipient={'address':to_address},
            sender={'address':from_address})
        if response.status_code != 200:
            logger.error('Error sending message %s to user %s', \
                         mailid, to_address)
