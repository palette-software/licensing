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
     'value':'Tableau2015!'},
    {'key':'SALESFORCE-TOKEN',
     'value':'GtjDrVqnGImDkgjc2LJgLIgip'},
    {'key':'TRIAL-REQ-EXPIRATION-DAYS',
     'value':'30'},
    {'key':'TRIAL-REG-EXPIRATION-DAYS',
     'value':'14'},
    {'key':'BUY-EXPIRATION-MONTHS',
     'value':'12'},
    {'key':'BUY-URL',
     'value':'https://www.palette-software.com/subscribe'},
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
    {'key':'SENDWITHUS-TRIAL-REQUESTED-ID',
     'value':''},
    {'key':'SENDWITHUS-TRIAL-REQUESTED-VMWARE-ID',
     'value':'dc_wjm4uWv63GAGx7RQSAEvLF'},
    {'key':'SENDWITHUS-TRIAL-REQUESTED-PCLOUD-ID',
     'value':'dc_V5oNEyYqWhDKZKA39ZN8qL'},
    {'key':'SENDWITHUS-TRIAL-REQUESTED-DONTKNOW-ID',
     'value':'dc_HDbLsD7c9VBS9pkuwaoHJM'},
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
    {'key':'SENDWITHUS-REGISTERED-VERIFIED-ID',
     'value':''}
    ]

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(System).filter(System.key == key).one().value
        except NoResultFound:
            return None

