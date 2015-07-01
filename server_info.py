

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
    licenseid = Column(Integer, ForeignKey("license.id", ondelete='CASCADE'),
                       primary_key=True)
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

    @classmethod
    def upsert(cls, licenseid, details):
        session = get_session()
        for i in details.keys():
            prop = ServerInfo.get_by_license(licenseid, i)
            if prop is None:
                prop = ServerInfo()
                prop.licenseid = licenseid
                prop.key = i
                prop.value = details[i]
                session.add(prop)
                session.commit()
            else:
                prop.value = details[i]
                session.commit()

    @classmethod
    def get_dict_by_licenseid(cls, lid):
        session = get_session()
        try:
            rows = session.query(ServerInfo)\
               .filter(ServerInfo.licenseid == lid).all()
            keys = [i.key for i in rows]
            values = [i.value for i in rows]
            result = dict(zip(keys, values))
            return result
        except NoResultFound:
            return None
