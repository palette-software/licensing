from __future__ import absolute_import

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm.exc import NoResultFound

class License(Base):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'license'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    key = Column(String, nullable=False, unique=True)
    type = Column(String)
    n = Column(String)
    system_id = Column(String)
    trial = Column(Boolean, nullable=False)
    contact_time = Column(DateTime)
    expiration_time = Column(DateTime, nullable=False)
    creation_time = Column(DateTime, server_default=func.now())

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

