from __future__ import absolute_import

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from akiri.framework.sqlalchemy import Base

class Billing(Base):
    # pylint: disable=no-init
    __tablename__ = 'billing'
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey("license.id"),
                        unique=True, nullable=False)

    firstname = Column(String)
    lastname = Column(String)
    email = Column(String)
    phone = Column(String)
    address_line1 = Column(String)
    address_line2 = Column(String)
    city = Column(String)
    state = Column(String)
    zipcode = Column(String)
    country = Column(String)

    parent = relationship("License", uselist=False)

