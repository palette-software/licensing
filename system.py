from __future__ import absolute_import

from datetime import datetime
from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

class System(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'system'
    id = Column(Integer, primary_key=True)

    key = Column(String, nullable=False, unique=True)
    value = Column(String)

    creation_time = Column(DateTime, server_default=func.now())
    last_update = Column(DateTime, default=datetime.utcnow(),
                                    onupdate=datetime.utcnow())

    defaults = [{'key':'mailchimp_apikey',
                  'value':'d5aebaeab75930485df70f3b1385b72c-us3'},
                 {'key':'mailchimp_trial_requested_id', 
                  'value':'0a7d5afba4'},
                 {'key':'mailchimp_trial_registered_id',
                  'value': 'ce81d140b6'},
                 {'key':'mailchimp_trial_notinstalled_id',
                  'value':'9f45cccb54'},
                 {'key':'mailchimp_trial_noresponse_id', 
                  'value':'100'},
                 {'key':'mailchimp_trial_started_id',
                  'value':'ab5312669b'},
                 {'key':'mailchimp_trial_expired_id',
                  'value':'ceed178b73'},
                 {'key':'mailchimp_closed_won_id',
                  'value':'ab8178b620'},
                 {'key':'mailchimp_up_for_renewal_id',
                  'value':'200'},
                 {'key':'mailchimp_debug',
                  'value':'false'},
                 {'key':'salesforce_username',
                  'value':'licensing@palette-software.com'},
                 {'key':'salesforce_password',
                  'value':'Tableau2015!'},
                 {'key':'salesforce_token',
                  'value':'GtjDrVqnGImDkgjc2LJgLIgip'},
                 {'key':'trial_req_expiration_days',
                  'value':'30'},
                 {'key':'trial_reg_expiration_days',
                  'value':'14'},
                 {'key':'buy_expiration_months',
                  'value':'12'},
                 {'key':'buy_url',
                  'value':'https://palettesoftware.wufoo.com/forms/buy-palette/def'},
                 {'key':'bad_stage_url',
                  'value':'http://palette-software.com/'},
                 {'key':'license_check_interval',
                  'value':'60'}]

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(System).filter(System.key == key).one().value
        except NoResultFound:
            return None

