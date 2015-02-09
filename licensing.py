from __future__ import absolute_import

from datetime import datetime, timedelta
from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm.exc import NoResultFound

class License(Base):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'license'
    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False, unique=True)
    type = Column(String)
    n = Column(String)
    system_id = Column(String)
    stage = Column(String, nullable=False)

    contact_time = Column(DateTime)
    expiration_time = Column(DateTime, nullable=False)
    registration_start_time = Column(DateTime)
    trial_start_time = Column(DateTime)
    license_start_time = Column(DateTime)

    email = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    subdomain = Column(String)
    organization = Column(String)
    timezone = Column(String, nullable=False)
    hosting_type = Column(String)
    license_type = Column(String)
    license_cap = Column(Integer)
    phone = Column(String, nullable=False)
    website = Column(String, nullable=False)

    alt_billing = Column(Boolean, default=False)
    billing_fn = Column(String)
    billing_ln = Column(String)
    billing_email = Column(String)
    billing_phone = Column(String)
    billing_address_line1 = Column(String)
    billing_address_line2 = Column(String)
    billing_city = Column(String)
    billing_state = Column(String)
    billing_zip = Column(String)
    billing_country = Column(String)

    creation_time = Column(DateTime, server_default=func.now())
    last_update = Column(DateTime, default=datetime.utcnow(),
                                    onupdate=datetime.utcnow())

    @classmethod
    def get_by_name(cls, name):
        session = get_session()
        try:
            return session.query(License).filter(License.name == name).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(License).filter(License.key == key).one()
        except NoResultFound:
            return None

    def set_license_info(self, data):
        self.stage = data.get('stage')
        self.key = data.get('key')
        self.expiration_time = data.get('exp_time')
        self.email = data.get('email')
        self.firstname = data.get('fn')
        self.lastname = data.get('ln')
        self.subdomain = data.get('subdomain')
        self.organization = data.get('org')
        self.timezone = data.get('timezone')
        self.hosting_type = data.get('hosting_type')
        self.license_type = data.get('license_type')
        self.license_cap = data.get('license_cap')
        self.phone = data.get('phone')
        self.website = data.get('website')

    def set_alt_billing(self, data):
        self.alt_billing = True
        self.billing_fn = data['billing_fn']
        self.billing_ln = data['billing_ln']
        self.billing_address_line1 = data['billing_address_line1']
        self.billing_address_line2 = data['billing_address_line2']
        self.billing_city = data['billing_city']
        self.billing_state = data['billing_state']
        self.billing_zip = data['billing_zip']
        self.billing_country = data['billing_country']

