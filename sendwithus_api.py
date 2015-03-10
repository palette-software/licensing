import sendwithus

import logging
from system import System

logger = logging.getLogger('licensing')

class SendwithusAPI(object):

    @classmethod
    def subscribe_user(cls, mailid, from_address, to_address, data):
        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        response = api.start_on_drip_campaign(
            mailid,
            {'address':to_address},
            email_data=data,
            sender={'address':from_address})
        if response.status_code != 200:
            logger.error('Error subscribing user %s to %s', to_address, mailid)

    @classmethod
    def send_message(cls, mailid, from_address, to_address, data):
        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        response = api.send(
            email_id=mailid,
            email_data=data,
            recipient={'address':to_address},
            sender={'address':from_address})
        if response.status_code != 200:
            logger.error('Error sending message %s to user %s',
                         mailid, to_address)
