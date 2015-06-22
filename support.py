from __future__ import absolute_import

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.exc import NoResultFound

from licensing import License

class Support(Base):
    # pylint: disable=no-init
    __tablename__ = 'support'
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey("license.id"),
                        unique=True, nullable=False)
    port = Column(Integer, unique=True, nullable=False)
    active = Column(Boolean, nullable=False, default=False, server_default='0')

    parent = relationship("License", uselist=False,
                          backref=backref('support', uselist=False))

    @classmethod
    def find_active_port_by_key(cls, key):
        # pylint: disable=no-member
        session = get_session()
        try:
            return session.query(Support).join(License)\
                          .filter(License.key == key)\
                          .filter(Support.active == True)\
                          .one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_name(cls, name):
        session = get_session()
        try:
            return session.query(Support).join(License)\
                          .filter(License.name == name)\
                          .one()
        except NoResultFound:
            return None
