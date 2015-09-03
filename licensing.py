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

    # Contact email of the person who created this instance
    email = Column(String, nullable=False) # FIXME: unique

    # FIXME: move to Salesforce
    #  if 'Organization Website' is remove from /subscribe in SQS.
    website = Column(String)

    # AWS, VMWare or Palette Pro
    hosting_type = Column(String)

    # FIXME: move to a separate Palette Pro table.
    subdomain = Column(String)
    aws_zone = Column(String) # AWS availability zone
    access_key = Column(String)
    secret_key = Column(String)
    instance_id = Column(String)

    salesforceid = Column(String)
    amount = Column(Numeric) # FIXME: is this needed in licensing?
    plan = Column(String) # Plan name - if NULL use default

    # Stripe customer record
    stripeid = Column(String)

    # Last connection from the support functionality
    support_contact_time = Column(DateTime)

    # What repository to use for generating the image.
    repo = Column(String, nullable=False, default="production")

    # Is this an active record?
    active = Column(Boolean, nullable=False, default=True)

    creation_time = Column(DateTime, default=func.now(), nullable=False)
    last_update = Column(DateTime, default=func.now(),
                         onupdate=func.now(), nullable=False)

    stage = relationship('Stage')
    product = relationship('Product')

    # FIXME: rename
    def istrial(self):
        if not self.stage:
            return True
        return not self.stage.key == 'STAGE-CLOSED-WON'

    # FIXME: generalize
    def todict(self):

        license_type = self.type

        data = {'license-key': self.key,
                'license-type': license_type}
        data['product'] = self.product.key
        data['product-name'] = self.product.name

        if self.product.key != Product.PRO_KEY:
            if license_type == 'Core':
                data['license-desc'] = str(self.n) + ' Cores'
            elif license_type == 'Named-user':
                data['license-desc'] = str(self.n) + ' Named Users'

        if self.website:
            data['website'] = self.website
        if self.promo_code:
            data['promo'] = self.promo_code

        return data

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
