import sendwithus

SENDWITHUS_APIKEY='test_123f4ca3dc10f6fda73355ea69270970dab784f2'

REQUESTED='dc_6bGAYqsYyehRD5VahXpoz3'

class SendwithusAPI():
    @classmethod
    def subscribe_user(cls,  data):
        api = sendwithus.api(api_key=SENDWITHUS_APIKEY)
        api.start_on_drip_campaign(
            REQUESTED,
            {'address':data.email},
            email_data={'license': 'blue'},
            sender={'address': 'hello@palette-software.com'})
