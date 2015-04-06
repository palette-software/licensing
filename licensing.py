from __future__ import absolute_import

from datetime import datetime
from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm.exc import NoResultFound

class License(Base):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'license'
    id = Column(Integer, primary_key=True)

    # The license key
    key = Column(String, nullable=False, unique=True)

    # The Tableau License Type
    type = Column(String)

    # Name
    name = Column(String)

    # The tableau license count
    n = Column(Integer)

    # Autogenrated unique system GUID of the Palette Server
    system_id = Column(String)

    # Stage in try/buy workflow
    stageid = Column(Integer, ForeignKey("stage.id"))

    # Last connection from Palette Server to licensing
    contact_time = Column(DateTime)

    # Trial or Not
    trial = Column(Boolean, nullable=False)

    # Expiration date/time of this stage
    expiration_time = Column(DateTime, nullable=False)

    # Time/date of when the Trial got registered
    registration_start_time = Column(DateTime)

    # Time/date when the Trial was started
    trial_start_time = Column(DateTime)

    # Time/date when the Tableau was bought
    license_start_time = Column(DateTime)

    email = Column(String, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)

    # used for Palette Cloud
    subdomain = Column(String)

    # customer info
    organization = Column(String)
    timezone = Column(String)
    website = Column(String, nullable=False)
    phone = Column(String)
    admin_role = Column(String)
    promo_code = Column(String)
    stripeid = Column(String)

    # AWS, VMWare or Palette Cloud
    hosting_type = Column(String)
    # AWS availability zone
    aws_zone = Column(String)

    # Alternate biling contact
    #alt_billing = Column(Boolean, default=False)
    billing_fn = Column(String)
    billing_ln = Column(String)
    billing_email = Column(String)
    billing_phone = Column(String)

    # Billing info
    billing_address_line1 = Column(String)
    billing_address_line2 = Column(String)
    billing_city = Column(String)
    billing_state = Column(String)
    billing_zip = Column(String)
    billing_country = Column(String)

    #amount = Column(Numeric(8, 2))

    access_key = Column(String)
    secret_key = Column(String)

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

    @classmethod
    def get_expired_licenses(cls, stageid):
        session = get_session()
        now = datetime.utcnow()
        try:
            rows = session.query(License).filter(License.stageid == stageid) \
                                         .filter(License.expiration_time < now)
        except NoResultFound:
            return None
        return rows

    @classmethod
    def change_stage(cls, row, new, expiration=None):
        session = get_session()
        row.stage = new
        if expiration is None:
            row.expiration_time = expiration
        session.commit()
