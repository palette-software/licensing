from __future__ import absolute_import

from datetime import datetime
from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, func
from sqlalchemy import Boolean, String, Integer, DateTime, Numeric
from sqlalchemy.schema import ForeignKey

from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

# pylint: disable=unused-import
from stage import Stage
from product import Product
from billing import Billing

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

    # type of product
    productid = Column(Integer, ForeignKey("product.id"))

    # Last connection from Palette Server to licensing
    contact_time = Column(DateTime)

    # Expiration date/time of this stage
    expiration_time = Column(DateTime, nullable=False)

    # Time/date of when the Trial got registered
    registration_start_time = Column(DateTime)

    # Time/date when the Trial was started
    trial_start_time = Column(DateTime)

    # Time/date when the Tableau was bought
    license_start_time = Column(DateTime)

    # Promotion code / coupon
    promo_code = Column(String) # can't be in billing

    # FIXME: move to a customer table
    email = Column(String, nullable=False) # FIXME: unique
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    organization = Column(String)
    timezone = Column(String)
    website = Column(String)
    phone = Column(String)
    admin_role = Column(String)

    # AWS, VMWare or Palette Pro
    hosting_type = Column(String)

    # FIXME: move to a separate Palette Pro table.
    subdomain = Column(String)
    aws_zone = Column(String) # AWS availability zone
    access_key = Column(String)
    secret_key = Column(String)

    salesforceid = Column(String)
    amount = Column(Numeric) # FIXME: move to billing?

    # Last connection from the support functionality
    support_contact_time = Column(DateTime)

    # What repository to use for generating the image.
    repo = Column(String, nullable=False, default="production")

    # Is this an active record?
    active = Column(Boolean, nullable=False, default=True)

    creation_time = Column(DateTime, server_default=func.now())
    last_update = Column(DateTime, default=datetime.utcnow(),
                                    onupdate=datetime.utcnow())

    stage = relationship('Stage')
    product = relationship('Product')
    billing = relationship('Billing', uselist=False, lazy='joined')

    # FIXME: rename
    def istrial(self):
        if not self.stage:
            return True
        return not self.stage.key == 'STAGE-CLOSED-WON'

    @classmethod
    def get_by_name(cls, name):
        session = get_session()
        try:
            return session.query(License).filter(License.name == name).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_email(cls, email):
        session = get_session()
        try:
            rows = session.query(License).filter(License.email == email).one()
        except NoResultFound:
            return None
        return rows

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
