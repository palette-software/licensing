from __future__ import absolute_import

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy.schema import ForeignKey, UniqueConstraint

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

class ServerInfo(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'server_info'

    id = Column(Integer, autoincrement=True, primary_key=True)

    # id in licensing table
    licenseid = Column(Integer, ForeignKey("license.id"), primary_key=True)
    key = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint('licenseid', 'key'),)

    @classmethod
    def get_by_license(cls, lid, key):
        session = get_session()
        try:
            return session.query(ServerInfo)\
               .filter(ServerInfo.key == key and ServerInfo.licenseid == lid)\
               .one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_id(cls, propid):
        session = get_session()
        try:
            return session.query(ServerInfo).filter(ServerInfo.id == propid)\
                           .one()
        except NoResultFound:
            return None

