#!/usr/bin/python

import time

from akiri.framework.sqlalchemy import create_engine, get_session
from licensing import License
from salesforce_api import SalesforceAPI
from mailchimp_api import MailchimpAPI

from config import get_config, get_config_float
import logging

# Setup logging
logger = logging.getLogger('license manager')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(\
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class LicenseManager():
    def CheckExpired(self):
        logger.info('Checking Licenes')
        requested = get_config('sf_stage_trial_requested')
        registered = get_config('sf_stage_trial_registered')
        started = get_config('sf_stage_trial_started')
        expired = get_config('sf_stage_trial_expired')
        won = get_config('sf_stage_closed_won')
        not_installed = get_config('sf_stage_trial_notinstalled')
        no_response = get_config('sf_stage_trial_noresponse')
        renewal = get_config('sf_stage_up_for_renewal')

        rows = License.get_expired_licenses(requested)
        for i in rows:
            logger.info('Trial requests expired {0}'.format(i))
            License.change_stage(i, not_installed)
            salesforce.update_opportunity(i)
            mailchimp.subscribe_user(\
                             get_config('mailchimp_trial_notinstalled_id', i))

        rows = License.get_expired_licenses(registered)
        for i in rows:
            logger.info('Expired Registrations {0}'.format(i))
            License.change_stage(i, no_response)
            salesforce.update_opportunity(i)
            mailchimp.subscribe_user(\
                             get_config('mailchimp_trial_noresponse_id', i))

        rows = License.get_expired_licenses(started)
        for i in rows:
            logger.info('Expired Trials {0}'.format(i))
            License.change_stage(i, expired)
            salesforce.update_opportunity(i)
            mailchimp.subscribe_user(\
                             get_config('mailchimp_trial_expired_id', i))

        rows = License.get_expired_licenses(won)
        for i in rows:
            logger.info('Expired Closed Won {0}'.format(i))
            License.change_stage(i, renewal)
            salesforce.update_opportunity(i)
            mailchimp.subscribe_user(\
                             get_config('mailchimp_up_for_renewal_id', i))

    """
    """
    def Start(self):
        while True:
           self.CheckExpired()
           time.sleep(get_config_float('license_check_interval'))

if __name__ == '__main__':
    # pylint: disable=invalid-name
    create_engine(get_config('db_url'), \
                  echo=False, pool_size=20, max_overflow=50)
    manager = LicenseManager()
    manager.Start()
