#!/usr/bin/env python
import sys
sys.path.append('/opt/palette')

from datetime import datetime
from dateutil.relativedelta import relativedelta
from webob import exc
import uuid
import time
import json
import logging

from akiri.framework import GenericWSGIApplication
from akiri.framework.route import Router
from akiri.framework.middleware.sqlalchemy import SessionMiddleware
from akiri.framework.sqlalchemy import create_engine, get_session
from akiri.framework.util import required_parameters

from licensing import License
from support import Support
from mailchimp_api import MailchimpAPI
from salesforce_api import SalesforceAPI

import config


# FIXME: https
LICENSE_EXPIRED = 'http://www.palette-software.com/license-expired'
TRIAL_EXPIRED = 'http://www.palette-software.com/trial-expired'
BUY = 'http://www.palette-software.com/buy'

def time_from_today(hours=0, days=0, months=0):
    return datetime.today() + relativedelta(hours=hours, days=days, months=months)

class LicensingApplication(GenericWSGIApplication):

    @required_parameters('system-id', 'license-key', \
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()
        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            # FIXME: notify
            pass
        entry.system_id = system_id
        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            # FIXME: notify
            pass
        entry.type = license_type
        license_quantity = req.params['license-quantity']
        if entry.n and entry.n != license_quantity:
            # FIXME: notify
            pass
        entry.n = license_quantity
        session = get_session()
        session.commit()
        return {'trial': entry.trial,
                'expiration-time': str(entry.expiration_time)}

class SupportApplication(GenericWSGIApplication):

    def service_GET(self, req):
        if 'key' not in req.params:
            # Return 404 instead of bad request to 'hide' this URL.
            return exc.HTTPNotFound()
        entry = Support.find_active_port_by_key(req.params['key'])
        if entry is None:
            raise exc.HTTPNotFound()
        return {'port': entry.port}


class ExpiredApplication(GenericWSGIApplication):

    def __init__(self, base_url):
        super(ExpiredApplication, self).__init__()
        self.base_url = base_url

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # FIXME: take 'key' and resolve.
        raise exc.HTTPTemporaryRedirect(location=self.base_url)


class HelloApplication(GenericWSGIApplication):

    def service_GET(self, req):
        # pylint: disable=unused-argument
        # This could be tracked :).
        return str(datetime.now())

class TrialRequestApplication(GenericWSGIApplication):
    def service_POST(self, req):
        """ Handler for Try Palette Form Post
        """
        fn = req.params['Field1']
        ln = req.params['Field2']
        fullname = fn + " " + ln
        email = req.params['Field3']
        org = req.params['Field6']
        website = req.params['Field115']
        hosting_type = req.params['Field8']
        subdomain = req.params['Field9']

        print 'New trial request for {0} {1} {2}'\
              .format(org, fullname, email)

        # fixme add exception handling
        entry = License()
        names = ['Field1', 'Field2', 'Field3', 'Field6', \
                 'Field115', 'Field8', 'Field9']
        fields = ['firstname', 'lastname', 'email', 'organization', \
                  'website', 'hosting_type', 'subdomain']
        entry.set_fields(req.params, names, fields)
        entry.key = str(uuid.uuid4())
        entry.expiration_time = time_from_today(days=config.TRIAL_REQ_EXPIRATION_DAYS) 
        entry.stage = config.SF_STAGE_TRIAL_REQUESTED

        session = get_session()
        session.add(entry)
        session.commit()

        # create or use an existing opportunity
        SalesforceAPI.new_opportunity(entry)

        # subscribe the user to the trial workflow if not already
        MailchimpAPI.subscribe_user(config.MAILCHIMP_TRIAL_REQUESTED_ID, \
                                    entry)

        print 'Trial request success for {0} {1}'.format(entry.email, entry.key)

        return 'license-key={0}'.format(key)

class TrialRegisterApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key', \
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        """
        """
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()

        print 'Processing Trial Registration for key {0}'.format(key)
        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            print 'Invalid trial register request for key {0}. \
                   System id from request {1} doesnt match DB {2}'\
                   .format(key, system_id, entry.system_id)
        entry.system_id = system_id

        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            print 'Invalid trial register request for key {0}. \
                   License Type from request {1} doesnt match DB {2}'\
                   .format(key, license_type, entry.type)
        entry.type = license_type

        license_quantity = req.params['license-quantity']
        if entry.n and entry.n != license_quantity:
            print 'Invalid trial register request for key {0}. \
                   License Type from request {1} doesnt match DB {2}'\
                   .format(key, license_quantitity, entry.n)
        entry.n = license_quantity

        entry.stage = config.SF_STAGE_TRIAL_REGISTERED
        entry.expiration_time = time_from_today(days=config.TRIAL_REQ_EXPIRATION_DAYS)
        session = get_session()
        session.commit()

        print 'Trial Registration for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time)

        return {'trial': True,
                'stage': entry.stage,
                'expiration-time': str(entry.expiration_time)}

class TrialStartApplication(GenericWSGIApplication):
    @required_parameters('system-id', 'license-key', \
                         'license-type', 'license-quantity')
    def service_POST(self, req):
        """
        """
        key = req.params['license-key']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()

        print 'Processing Trial Start for key {0}'.format(key)
        system_id = req.params['system-id']
        if entry.system_id and entry.system_id != system_id:
            print 'Invalid trial start request for key {0}. \
                   System id from request {1} doesnt match DB {2}'\
                   .format(key, system_id, entry.system_id)
        entry.system_id = system_id

        license_type = req.params['license-type']
        if entry.type and entry.type != license_type:
            print 'Invalid trial start request for key {0}. \
                   License Type from request {1} doesnt match DB {2}'\
                   .format(key, license_type, entry.type)
        entry.type = license_type

        license_quantity = req.params['license-quantity']
        if entry.n and entry.n != license_quantity:
            print 'Invalid trial start request for key {0}. \
                   License Type from request {1} doesnt match DB {2}'\
                   .format(key, license_quantitity, entry.n)
        entry.n = license_quantity

        entry.stage = config.SF_STAGE_TRIAL_STARTED
        entry.expiration_time = time_from_today(days=config.TRIAL_REG_EXPIRATION_DAYS)
        session = get_session()
        session.commit()

        print 'Trial Start for key {0} success. Expiration {1}'\
              .format(key, entry.expiration_time)

        return {'trial': True,
                'stage': entry.stage,
                'expiration-time': str(entry.expiration_time)}

class BuyRequestApplication(GenericWSGIApplication):
    def service_GET(self, req):
        """ Handle get request which looks up the key and redirects to a
            URL to buy with the info pre-populated on the form
        """
        key = req.params_get('key')
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()

        print 'Returning buy request info for {0}'.format(key)

        fields = [7, 3, 4, 5, 6, 21, 9]
        fieldnames = ['field{0}'.format(i) for i in fields]
        values = [entry.key, entry.firstname, entry.lastname, entry.email, \
                  entry.organization, entry.phone, entry.n]
        parameters = dict(zip(fieldnames, values))
        url_items = [str(k) + '=' + str(v) for k, v in parameters.iteritems()]
        url = '&'.join(url_items)
        location = '{0}/{1}'.format(config.BUY_URL, url)
        raise exc.HTTPTemporaryRedirect(location=location)

    def service_POST(self, req):
        """
        """
        key = req.params['Field7']
        entry = License.get_by_key(key)
        if entry is None:
            raise exc.HTTPNotFound()

        print 'Buy request for {0}'.format(key)

        names = ['Field3', 'Field4', 'Field6', 'Field5', 'Field21', \
                 'Field22', 'Field8', 'Field9', 'Field13', \
                 'Field14', 'Field15', 'Field16', 'Field17', 'Field18']
        fields = ['firstname', 'lastname', 'organization', 'email', 'phone', \
                  'palette_type', 'license_type', 'license_cap', \
                  'billing_address_line1', 'billing_address_line2', \
                  'billing_city', 'billing_state', 'billing_zip', 'billing_country']
        entry.set_fields(req.params, names, fields)

        alt_billing = req.params['Field225']
        if alt_billing == ' ':
            entry.alt_billing = True
            names = ['Field11', 'Field12', 'Field20', 'Field19', 'Field13', \
                     'Field14', 'Field15', 'Field16', 'Field17', 'Field18']
            fields = ['billing_fn', 'billing_ln', 'billing_email', 'billing_phone']
            entry.set_fields(req.params, names, fields)

        entry.expiration_time = time_from_today(months=config.BUY_EXPIRATION_MONTHS)
        entry.stage = config.SF_STAGE_CLOSED_WON
        session = get_session()
        session.commit()

        print 'Buy request success for {0}'.format(key)

class LicenseProcess():
    def CheckExpired(self):
        rows = License.get_expired_licenses(config.SF_STAGE_TRIAL_REQUESTED)
        for i in rows:
            print 'Trial requests expired {0}'.format(i)
            License.change_stage(i, config.SF_STAGE_TRIAL_NOT_INSTALLED)

        rows = License.get_expired_licenses(config.SF_STAGE_TRIAL_REGISTERED)
        for i in rows:
            print 'Expired Registrations {0}'.format(i)
            License.change_stage(i, config.SF_STAGE_NO_RESPONSE)

        rows = License.get_expired_licenses(config.SF_STAGE_TRIAL_STARTED)
        for i in rows:
            print 'Expired Trials {0}'.format(i)
            License.change_stage(i, config.SF_STAGE_TRIAL_EXPIRED)

        rows = License.get_expired_licenses(config.SF_STAGE_CLOSED_WON)
        for i in rows:
            print 'Expired Closed Won {0}'.format(i)
            License.change_stage(i, config.SF_STAGE_UP_FOR_RENEWAL)

    """
    """
    def Start(self):
        while True:
           CheckExpired()
           time.sleep(1000)

# pylint: disable=invalid-name
create_engine(config.DB_URL, echo=False)

router = Router()
router.add_route(r'/hello\Z', HelloApplication())
router.add_route(r'/license\Z', LicensingApplication())
router.add_route(r'/support\Z', SupportApplication())
router.add_route(r'/trial-expired\Z', ExpiredApplication(TRIAL_EXPIRED))
router.add_route(r'/license-expired\Z', ExpiredApplication(LICENSE_EXPIRED))
router.add_route(r'/buy\Z', ExpiredApplication(BUY))

router.add_route(r'/api/licensing/trial_request\Z', TrialRequestApplication())
router.add_route(r'/api/licensing/trial_register\Z', TrialRegisterApplication())
router.add_route(r'/api/licensing/trial_start\Z', TrialStartApplication())
router.add_route(r'/api/licensing/buy_request', BuyRequestApplication())

application = SessionMiddleware(config.DB_URL, app=router)

if __name__ == '__main__':
    from akiri.framework.server import runserver

    router.add_redirect(r'/\Z', 'http://www.palette-software.com')
    runserver(application, use_reloader=True, host='0.0.0.0')
