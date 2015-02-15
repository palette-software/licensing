#!/usr/bin/python

import time

from akiri.framework.sqlalchemy import create_engine, get_session
from licensing import License

import config

class LicenseManager():
    def CheckExpired(self):
        print 'Checking Licenes'

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
           self.CheckExpired()
           time.sleep(1)

if __name__ == '__main__':
    # pylint: disable=invalid-name
    create_engine(config.DB_URL, echo=False, pool_size=20, max_overflow=50)
    manager = LicenseManager()
    manager.Start()
