import sendwithus

import logging
from system import System

logger = logging.getLogger('licensing')

class SendwithusAPI():
    @classmethod
    def subscribe_user(cls,  mailid, data):
        apikey = System.get_by_key('SENDWITHUS-APIKEY')
        api = sendwithus.api(api_key=apikey)
        r = api.start_on_drip_campaign(
            mailid,
            {'address':data.email},
            email_data={'license':data.key, 'firstname':data.firstname},
            sender={'address': 'hello@palette-software.com'})
        if r.status_code != 200:
            logger.error('Error subscribing user {0} to {1}'.format(\
                   data.email, mailid))
