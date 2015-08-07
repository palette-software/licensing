# This module handles the actual purchase of a product.
import logging
from datetime import datetime, timedelta
from webob import exc

import stripe
from simple_salesforce import SalesforceError

from akiri.framework import GenericWSGIApplication
from akiri.framework.util import required_parameters
from akiri.framework.sqlalchemy import get_session # FIXME

from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI

from licensing import License
from plan import Plan
from stage import Stage
from system import System

from utils import to_localtime, dict_to_qs

logger = logging.getLogger('licensing')

def error_notify(msg, data=None):
    if data:
        msg = msg + "\n" + str(data)
    logger.error(msg)
    SlackAPI.notify(msg)

def sqs_phone(req, prefix=None):
    """
    Converts a Squarespace phone number field into a string.
    Returns None if the phone number was not provided.
    """
    if not prefix:
        prefix = ""
    else:
        if not prefix.endswith('-'):
            prefix = prefix + '-'
    phone = ""
    if prefix + 'country' in req.params:
        value = req.params[prefix + 'country']
        if value:
            phone = value + '-'
    value = req.params[prefix + 'areacode']
    if not value:
        return None
    phone = phone + value + '-'
    value = req.params[prefix + 'prefix']
    if not value:
        return None
    phone = phone + value + '-'
    value = req.params[prefix + 'line']
    if not value:
        return value
    return phone + value

def build_contact(req):
    """Take the request data and translate the fields so that the resulting
    data is suitable for a Salesforce contact insert or update."""
    data = {}
    data['Email'] = req.params['email']
    data['FirstName'] = req.params['fname']
    data['LastName'] = req.params['lname']
    data['Title'] = req.params['Title']
    data['Department'] = req.params['Department']
    #data['Account'] = req.params['Organization']

    data['Phone'] = sqs_phone(req, 'Primary-Phone')

    altphone = sqs_phone(req, 'Alt-Phone')
    if altphone:
        data['OtherPhone'] = altphone
    return data

def build_opportunity(entry):
    """Extract opportunity data from a licensing entry."""
    # FIXME: merge with SalesforceAPI.update_opportunity()
    data = {'Palette_Domain_ID__c':entry.id,
            'StageName':Stage.get_by_id(entry.stageid).name,
            'CloseDate':entry.expiration_time.isoformat(),
            'Expiration_Date__c':entry.expiration_time.isoformat(),
            'Tableau_App_License_Type__c':entry.type,
            'Tableau_App_License_Count__c':entry.n,
            'System_ID__c':entry.system_id,
            'Hosting_Type__c':entry.hosting_type,
            'AWS_Region__c':entry.aws_zone,
            'Access_Key__c':entry.access_key,
            'Secret_Access_Key__c':entry.secret_key,
            'Palette_Cloud_subdomain__c':entry.subdomain,
            'Promo_Code__c':entry.promo_code}
    if entry.amount is not None:
        data['Amount'] = float(entry.amount)
    if entry.productid is not None:
        data['Palette_Plan__c'] = entry.product.name
    if entry.registration_start_time is not None:
        data['Trial_Request_Date_Time__c'] = \
                                entry.registration_start_time.isoformat()
    if entry.trial_start_time is not None:
        data['Trial_Registered_Date_Time__c'] = \
                                entry.trial_start_time.isoformat()
    if entry.license_start_time is not None:
        data['License_Start_Date_Time__c'] = \
                                entry.license_start_time.isoformat()
    return data

def build_account(req):
    """Take the request data and translate the fields so that the resulting
    data is suitable for a Salesforce account update."""
    data = {}

    name = req.params['Billing-fname'] + " " + req.params['Billing-lname']
    data['Name_on_Card__c'] = name

    address = req.params['address']

    address2 = req.params['address2']
    if address2:
        address = address + ', ' + address2

    data['BillingStreet'] = address
    data['BillingCity'] = req.params['city']
    data['BillingState'] = req.params['state']
    data['BillingPostalCode'] = req.params['zipcode']
    data['BillingCountry'] = req.params['country']
    data['Billing_Email__c'] = req.params['Billing-email']
    data['Billing_Phone__c'] = sqs_phone(req, 'Billing-Phone')
    return data

class SubscribeApplication(GenericWSGIApplication):
    """
    This is the handler thats called when a user hits the 'Subscribe'
    button in the main application.
    This handler does the following:
      - Looks up the account based on the license-key passed via POST
      - Redirects the user to the appropriate webpage based on account type.
      - Sends the account information as query string parameters.
    """

    def service_GET(self, req):
         # pylint: disable=too-many-locals
        """ Handle get request which looks up the key and redirects to a
            URL to subscribe with the info pre-populated on the form
            NOTE: never fail - always redirect to the subscribe page.
        """
        url = System.get_by_key('SUBSCRIBE-URL')

        key = req.params_get('key')
        if key:
            location = url + '?license-key=' + key
        else:
            logger.error('Subscribe request: no license key specified.')
            raise exc.HTTPTemporaryRedirect(location=url)

        entry = License.get_by_key(key)
        if entry is None:
            logger.error('Subscribe request key not found:' + key)
            raise exc.HTTPTemporaryRedirect(location=location)

        logger.info('Processing Subscribe GET request for ' + key)

        data = entry.todict()

        plan = Plan.get_from_license(entry)
        if not plan:
            # if agent hasn't connected, there is no plan available.
            logger.error('No plan available!')
            # FIXME: need an error page.
            raise exc.HTTPTemporaryRedirect(location=location)

        data['amount'] = plan.amount
        data['price'] = plan.price
        data['quantity'] = plan.quantity

        opportunity = SalesforceAPI.lookup_opportunity(key)
        if opportunity:
            opp_id = opportunity['Id']
            opp_name = opportunity['Name']
            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opp_id)
        else:
            opp_name = 'NONE'
            sf_url = 'UNKNOWN'
        is_expired = entry.expiration_time < datetime.utcnow()

        SlackAPI.notify('*Subscribe Browse Event:* '
                'Key: {0}, Opportunity: {1}, Name: {2} ({3}), '
                'Org: {4}, Type: {5} {6} Expiration {7} Expired: {8}' \
                .format(entry.key, opp_name,
                        entry.firstname + ' ' + entry.lastname, entry.email,
                        entry.organization, entry.hosting_type, sf_url,
                        to_localtime(entry.expiration_time).strftime("%x"),
                        is_expired))

        location = url + dict_to_qs(data)
        raise exc.HTTPTemporaryRedirect(location=location)

    @required_parameters('stripeToken')
    def service_POST(self, req):
        # pylint: disable=too-many-locals

        key = req.params_get('license-key')

        entry = License.get_by_key(key)
        if entry is None:
            error_notify("Subscribe request key not found '" + key + "'")
            # FIXME: re-route to a custom error page saying contact us.
            raise exc.HTTPNotFound()

        logger.info('Processing Subscribe get request info for ' + key)

        # first we charge them...
        token = req.POST['stripeToken']
        plan = Plan.get_from_license(entry)

        # FIXME: reflect PROMO_CODE on subscribe page pricing.

        if entry.promo_code:
            customer = stripe.Customer.create(source=token,
                                              plan=plan.name,
                                              quantity=plan.quantity,
                                              coupon=entry.promo_code,
                                              email=entry.email)
        else:
            customer = stripe.Customer.create(source=token,
                                              plan=plan.name,
                                              quantity=plan.quantity,
                                              email=entry.email)
        entry.amount = plan.amount
        entry.stripeid = customer.id

        now = datetime.utcnow()
        entry.license_start_time = now
        entry.expiration_time = now + timedelta(365*10) # ten years
        entry.stageid = Stage.get_by_key('STAGE-CLOSED-WON').id

        # FIXME:
        session = get_session()
        session.commit()

        email_data = entry.email_data()

        # FIXME: send this to the billing email too.
        # subscribe the user to the trial workflow if not already
        SendwithusAPI.subscribe_user('SENDWITHUS-CLOSED-WON-ID',
                                     'hello@palette-software.com',
                                     req.params['Email'],
                                     email_data)

        #SendwithusAPI.send_message('SENDWITHUS-SUBSCRIBE-NOTIFICATION-ID',
        #                           'licensing@palette-software.com',
        #                           'hello@palette-software.com',
        #                            email_data) # FIXME: needs billing info

        # use 302 here so that the browswer redirects with a GET request.
        url = System.get_by_key('SUBSCRIBE-REDIRECT-URL')

        try:
            sf = SalesforceAPI.connect()
        except StandardError:
            error_notify('Unable to connect to Salesforce', req.params)
            return exc.HTTPFound(location=url)

        try:
            opportunity = SalesforceAPI.get_opportunity_by_key(sf, key)
            if opportunity is None:
                error_notify("No opportunity for key : " + key)
                return exc.HTTPFound(location=url)

            account_id = opportunity['AccountId']

            # FIXME: add 'Contact Role'
            SalesforceAPI.upsert_contact(sf, account_id, build_contact(req))

            sf.Account.update(account_id, build_account(req))
            sf.Opportunity.update(opportunity['Id'], build_opportunity(entry))
        except (SalesforceError, StandardError), ex:
            # SalesforceError doesn't inherit from StandardError
            error_notify('Salesforce ERROR: ' + str(ex), req.params)
            return exc.HTTPFound(location=url)

        sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(), opportunity['Id'])
        SlackAPI.notify('*{0}* Opportunity: {1} ({2}) : {3}'
                        .format(Stage.get_stage_name(entry.stageid),
                                opportunity['Name'],
                                entry.email,
                                sf_url))
        # FIXME: temporary
        SlackAPI.notify(str(req.params))

        logger.info('Subscribe request succeeded for {0}'.format(key))
        return exc.HTTPFound(location=url)
