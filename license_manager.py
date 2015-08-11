#!/usr/bin/python

import time

import sys
sys.path.append('/opt/palette')

from datetime import datetime
import uuid
import logging

from akiri.framework.sqlalchemy import get_session

from contact import Email
from stage import Stage
from licensing import License
from system import System
from product import Product
from utils import get_netloc, domain_only, translate_values
from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI
from boto_api import BotoAPI

logger = logging.getLogger('licensing')

# pylint: disable=too-many-arguments

class LicenseManager(object):
    @classmethod
    def _check_expired(cls):
        logger.info('C7hecking Licenses')

        requested = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id
        registered = Stage.get_by_key('STAGE-TRIAL-REGISTERED').id
        started = Stage.get_by_key('STAGE-TRIAL-STARTED').id
        expired = Stage.get_by_key('STAGE-TRIAL-EXPIRED').id
        won = Stage.get_by_key('STAGE-CLOSED-WON').id
        not_installed = Stage.get_by_key('STAGE-TRIAL-NOTINSTALLED').id
        no_response = Stage.get_by_key('STAGE-TRIAL-NORESPONSE').id
        renewal = Stage.get_by_key('STAGE-UP-FOR-RENEWAL').id

        from_email = 'hello@palette-software.com'

        rows = License.get_expired_licenses(requested)
        for i in rows:
            logger.info('Trial requests expired {0}'.format(i))
            License.change_stage(i, not_installed)
            SalesforceAPI.update_opportunity(i)
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-EXPIRED-ID',
                                         from_email,
                                         i.email,
                                         {}) # FIXME: populate_email_data(i))

        rows = License.get_expired_licenses(registered)
        for i in rows:
            logger.info('Expired Registrations {0}'.format(i))
            License.change_stage(i, no_response)
            SalesforceAPI.update_opportunity(i)
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-EXPIRED-ID',
                                         from_email,
                                         i.email,
                                         {}) # FIXME: populate_email_data(i))

        rows = License.get_expired_licenses(started)
        for i in rows:
            logger.info('Expired Trials {0}'.format(i))
            License.change_stage(i, expired)
            SalesforceAPI.update_opportunity(i)
            SendwithusAPI.subscribe_user('SENDWITHUS-TRIAL-EXPIRED-ID',
                                         from_email,
                                         i.email,
                                         {}) # FIXME: populate_email_data(i))

        rows = License.get_expired_licenses(won)
        for i in rows:
            logger.info('Expired Closed Won {0}'.format(i))
            License.change_stage(i, renewal)
            SalesforceAPI.update_opportunity(i)
            SendwithusAPI.subscribe_user('SENDWITHUS-LICENSE-EXPIRED-ID',
                                         from_email,
                                         i.email,
                                         {}) # FIXME: populate_email_data(i))

    @classmethod
    def monitor(cls):
        """ Starts a periodic check of the licenes
            May be moot is script is run from con
        """
        sleep_interval = float(System.get_by_key('LICENSE-CHECK-INTERVAL'))
        while True:
            cls._check_expired() # FIXME: broken due to populate_email_data
            time.sleep(sleep_interval)

    REGISTER_FIELDS = {
        'firstname':'firstname',
        'lastname':'lastname',
        'email':'email',
        'name':'name'
    }

    # FIXME: merge with trial? and fix signature
    @classmethod
    def new_license(cls, params, contact, product, stage,
                         expiration, mailid, send_email=True):
        """ Handle licensing for a new user
        """
        # pylint: disable=too-many-locals
        # FIXME
        session = get_session()

        firstname = params['firstname']
        lastname = params['lastname']
        email = Email(params['email'])

        entry = License.get_by_name(params['name'])
        if entry is not None:
            logger.info('License already exists for %s %s %s %s',
                        entry.name, firstname, lastname, email)
            return
        else:
            entry = License()
            translate_values(params, entry, cls.REGISTER_FIELDS)
            logger.info('Generating new license for %s  %s %s %s',
                        entry.name, firstname, lastname, email)

            entry.key = str(uuid.uuid4())
            entry.stageid = Stage.get_by_key(stage).id
            entry.registration_start_time = datetime.utcnow()
            entry.expiration_time = expiration
            entry.organization = get_netloc(domain_only(entry.email)).lower()
            entry.website = entry.organization
            entry.subdomain = params['name']
            entry.name = entry.subdomain
            entry.productid = Product.get_by_key(product).id
            if entry.productid == Product.get_by_key('PALETTE-PRO').id:
                entry.aws_zone = BotoAPI.get_region_by_name(entry.aws_zone)
                entry.access_key, entry.secret_key = BotoAPI.create_s3(entry)
            entry.salesforceid = SalesforceAPI.new_opportunity(entry)

            session.add(entry)
            session.commit()

            # notify slack
            sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(),
                                      entry.salesforceid)
            SlackAPI.notify('*{0}* Generated New License for: '
                    '{1} ({2}) {3}'.format(
                    Stage.get_stage_name(entry.stageid),
                    SalesforceAPI.get_opportunity_name(entry),
                    entry.email,
                    sf_url))

            email_data = SendwithusAPI.gather_email_data(contact, entry)
            if send_email:
                # subscribe the user to the trial workflow if not already
                SendwithusAPI.subscribe_user(mailid,
                                             'hello@palette-software.com',
                                             entry.email,
                                             email_data)

            SendwithusAPI.send_message(mailid,
                                       'licensing@palette-software.com',
                                       'hello@palette-software.com',
                                       email_data)

            logger.info('Generated new License Name {0} Key {1} success.'\
                       .format(entry.name, entry.key))

            return entry

# pylint: disable=too-many-branches
    @classmethod
    def update_license(cls, params):
        """ Update the information for a license in the DB and in salesforce"""
        session = get_session()
        entry = None
        if 'name' in params:
            entry = License.get_by_name(params['name'])
            if entry is None:
                logger.info('Could not find specified license by name %s',
                            params['name'])
        if 'key' in params:
            entry = License.get_by_key(params['key'])
            if entry is None:
                logger.info('Could not find specified license by key %s',
                            params['key'])
        if entry is None:
            return

        if 'expiration_time' in params:
            entry.expiration_time = params['expiration_time']

        if 'organization' in params:
            entry.organization = params['organization']

        if 'website' in params:
            entry.website = params['website']

        if 'subdomain' in params:
            entry.subdomain = params['subdomain']

        if 'lastname' in params:
            entry.lastname = params['lastname']

        if 'firstname' in params:
            entry.firstname = params['firstname']

        if 'email' in params:
            entry.email = params['email']

        if 'stageid' in params:
            entry.stageid = params['stageid']

        session.commit()

        SalesforceAPI.update_opportunity(entry)

        sf_url = '{0}/{1}'.format(SalesforceAPI.get_url(),
                                  entry.salesforceid)
        SlackAPI.notify('*{0}* Updated Licensing: '
                    '{1} new values ({2}) {3}'.format(
                    Stage.get_stage_name(entry.stageid),
                    SalesforceAPI.get_opportunity_name(entry),
                    params,
                    sf_url))

        logger.info('Updated license name %s parameters %s', entry.name, params)
