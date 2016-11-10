#!/usr/bin/python

import time

import sys
sys.path.append('/opt/palette')

import logging

from stage import Stage
from licensing import License
from system import System

logger = logging.getLogger('licensing')

# pylint: disable=too-many-arguments

class LicenseManager(object):
    @classmethod
    def _check_expired(cls):
        logger.info('Checking Licenses')

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

        rows = License.get_expired_licenses(registered)
        for i in rows:
            logger.info('Expired Registrations {0}'.format(i))
            License.change_stage(i, no_response)

        rows = License.get_expired_licenses(started)
        for i in rows:
            logger.info('Expired Trials {0}'.format(i))
            License.change_stage(i, expired)

        rows = License.get_expired_licenses(won)
        for i in rows:
            logger.info('Expired Closed Won {0}'.format(i))
            License.change_stage(i, renewal)

    @classmethod
    def monitor(cls):
        """ Starts a periodic check of the licenes
            May be moot is script is run from con
        """
        sleep_interval = float(System.get_by_key('LICENSE-CHECK-INTERVAL'))
        while True:
            cls._check_expired() # FIXME: broken due to populate_email_data
            time.sleep(sleep_interval)
