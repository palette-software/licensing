#!/usr/bin/python

import time

from akiri.framework.sqlalchemy import create_engine, get_session
from licensing import License
from salesforce_api import SalesforceAPI
from sendwithus_api import SendwithusAPI

import config
import logging
from stage import Stage
from system import System

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
        logger.info('Checking Licenses')

        requested = Stage.get_by_key('STAGE-TRIAL-REQUESTED').id
        registered = Stage.get_by_key('STAGE-TRIAL-REGISTERED').id
        started = Stage.get_by_key('STAGE-TRIAL-STARTED').id
        expired = Stage.get_by_key('STAGE-TRIAL-EXPIRED').id
        won = Stage.get_by_key('STAGE-CLOSED-WON').id
        not_installed = Stage.get_by_key('STAGE-TRIAL-NOTINSTALLED').id
        no_response = Stage.get_by_key('STAGE-TRIAL-NORESPONSE').id
        renewal = Stage.get_by_key('STAGE-UP-FOR-RENEWAL').id

        rows = License.get_expired_licenses(requested)
        for i in rows:
            logger.info('Trial requests expired {0}'.format(i))
            License.change_stage(i, not_installed)
            salesforce.update_opportunity(i)
            SendwithusAPI.subscribe_user(\
                 System.get_by_key('SENDWITHUS-TRIAL-NOTINSTALLED-ID', i))

        rows = License.get_expired_licenses(registered)
        for i in rows:
            logger.info('Expired Registrations {0}'.format(i))
            License.change_stage(i, no_response)
            salesforce.update_opportunity(i)
            SendwithusAPI.subscribe_user(\
                 System.get_by_key('SENDWITHUS-TRIAL-NORESPONSE-ID', i))

        rows = License.get_expired_licenses(started)
        for i in rows:
            logger.info('Expired Trials {0}'.format(i))
            License.change_stage(i, expired)
            salesforce.update_opportunity(i)
            SendwithusAPI.subscribe_user(\
                 System.get_by_key('SENDWITHUS-TRIAL-EXPIRED-ID', i))

        rows = License.get_expired_licenses(won)
        for i in rows:
            logger.info('Expired Closed Won {0}'.format(i))
            License.change_stage(i, renewal)
            salesforce.update_opportunity(i)
            SendwithusAPI.subscribe_user(\
                 System.get_by_key('SENDWITHUS-UP-FOR-RENEWAL-ID', i))

    """
    """
    def Start(self):
        sleep_interval = float(System.get_by_key('LICENSE-CHECK-INTERVAL'))
        while True:
           self.CheckExpired()
           time.sleep(sleep_interval)

if __name__ == '__main__':
    # pylint: disable=invalid-name
    create_engine(config.db_url, \
                  echo=False, pool_size=20, max_overflow=50)
    manager = LicenseManager()
    manager.Start()
