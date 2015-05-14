from __future__ import absolute_import

from datetime import datetime
from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer, DateTime, func
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

    defaults = [\
    {'key':'SALESFORCE-USERNAME',
     'value':'licensing@palette-software.com'},
    {'key':'SALESFORCE-PASSWORD',
     'value':'Tableau2014!'},
    {'key':'SALESFORCE-TOKEN',
     'value':'HtKzxC8KpOKMOskGTSNTLxflo'},
    {'key':'TRIAL-REQ-EXPIRATION-DAYS',
     'value':'30'},
    {'key':'TRIAL-REG-EXPIRATION-DAYS',
     'value':'14'},
    {'key':'BUY-EXPIRATION-MONTHS',
     'value':'12'},
    {'key':'BUY-URL',
     'value':'https://palette-software.squarespace.com/subscribe'},
    {'key':'BAD-STAGE-URL',
     'value':'http://palette-software.com/'},
    {'key':'LICENSE-CHECK-INTERVAL',
     'value':'60'},
    {'key':'CORE-PRICE',
     'value':'2000'},
    {'key':'USER-PRICE',
     'value':'60'},
    {'key':'SEND-SLACK',
     'value':'true'},
    {'key':'SLACK-CHANNEL',
     'value':'customer-try-buy'},
    {'key':'CREATE-INSTANCE',
     'value':'true'},
    {'key':'SENDWITHUS-APIKEY',
     'value':''},
    {'key':'SENDWITHUS-TRIAL-REQUESTED-PRO-ID',
     'value':'dc_V5oNEyYqWhDKZKA39ZN8qL'},
    {'key':'SENDWITHUS-TRIAL-REQUESTED-ENT-ID',
     'value':''},
    {'key':'SENDWITHUS-TRIAL-NOTINSTALLED-ID',
     'value':''},
    {'key':'SENDWITHUS-TRIAL-NORESPONSE-ID',
     'value':''},
    {'key':'SENDWITHUS-TRIAL-STARTED-ID',
     'value':'dc_PC3NedL5KYoNFE4EjFxk4j'},
    {'key':'SENDWITHUS-TRIAL-EXPIRED-ID',
     'value':''},
    {'key':'SENDWITHUS-CLOSED-WON-ID',
     'value':''},
    {'key':'SENDWITHUS-UP-FOR-RENEWAL-ID',
     'value':''},
    {'key':'PALETTECLOUD-DNS-ZONE',
     'value':'palette-software.net'},
    {'key':'PALETTECLOUD-LAUNCH-SUCCESS-ID',
     'value':''},
    {'key':'PALETTECLOUD-LAUNCH-FAIL-ID',
     'value':''},
    {'key':'SENDWITHUS-BUY-NOTIFICATION-ID',
     'value':''},
    {'key':'SENDWITHUS-REGISTERED-UNVERIFIED-ID',
     'value':''},
    {'key':'TRIAL-REQUEST-REDIRECT-PRO-URL',
     'value':'http://www.palette-software.com/trial-confirmation-pro'},
    {'key':'TRIAL-REQUEST-REDIRECT-ENT-URL',
     'value':'http://www.palette-software.com/trial-confirmation-ent'},
    {'key':'REGISTER-REDIRECT-URL',
     'value':'http://www.palette-software.com/register-thank-you'},
    {'key':'REGISTER-VERIFY-URL',
     'value':'https://licensing.palette-software.com/api/verify'},
    {'key':'BUY-REDIRECT-URL',
     'value':'http://www.palette-software.com/subscribe-thank-you'},
    {'key':'VERIFY-REDIRECT-URL',
     'value':'http://www.palette-software.com/start-trial'},
    {'key':'PALETTE-PRO-PLAN',
     'value':'MONTHLY'},
    {'key':'PALETTE-PRO-COST',
     'value':'199'},
    {'key':'PALETTE-ENT-NAMED-USER-PLAN',
     'value':'ENTERPRISE_NU_M'},
    {'key':'PALETTE-ENT-NAMED-USER-COST',
     'value':'10'},
    {'key':'PALETTE-ENT-CORE-PLAN',
     'value':'ENTERPRISE_C_M'},
    {'key':'PALETTE-ENT-CORE-COST',
     'value':'200'},
    {'key':'SENDWITHUS-TRIAL-REQUESTED-ENT-INTERNAL-ID',
     'value':''},
    {'key':'SALESFORCE-URL',
     'value':''}
    ]

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(System).filter(System.key == key).one().value
        except NoResultFound:
            return None

