

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy.schema import ForeignKey, UniqueConstraint

from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

from datetime import datetime

class ServerInfo(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'server_info'

    id = Column(Integer, autoincrement=True, primary_key=True)

    # id in licensing table
    licenseid = Column(Integer, ForeignKey("license.id"), primary_key=True)
    key = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

    creation_time = Column(DateTime, server_default=func.now())
    last_update = Column(DateTime, default=datetime.utcnow(),
                                    onupdate=datetime.utcnow())

    __table_args__ = (UniqueConstraint('licenseid', 'key'),)

    @classmethod
    def get_by_license(cls, lid, key):
        session = get_session()
        try:
            return session.query(ServerInfo)\
               .filter(ServerInfo.key == key)\
               .filter(ServerInfo.licenseid == lid)\
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

