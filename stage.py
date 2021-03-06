from __future__ import absolute_import

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

class Stage(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'stage'

    id = Column(Integer, primary_key=True)

    key = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)

    defaults = [{'key' : 'STAGE-TRIAL-REQUESTED',
                 'name': 'Trial Requested'},
                {'key'  : 'STAGE-TRIAL-REGISTERED', # UNUSED
                 'name': 'Trial Registered'},
                {'key'  : 'STAGE-TRIAL-NOTINSTALLED', # UNUSED
                 'name': 'Trial Not Installed'},
                {'key'  : 'STAGE-TRIAL-NORESPONSE', # UNUSED
                 'name': 'Trial No Response'},
                {'key'  : 'STAGE-TRIAL-STARTED',
                 'name': 'Trial Started'},
                {'key'  : 'STAGE-TRIAL-EXPIRED',
                 'name': 'Trial Expired'},
                {'key'  : 'STAGE-TRIAL-EXTENDED', # UNUSED
                 'name': 'Trial Extended'},
                {'key'  : 'STAGE-LICENSE-EXPIRED',
                 'name': 'License Expired'},
                {'key'  : 'STAGE-UP-FOR-RENEWAL', # UNUSED
                 'name': 'Up For Renewal'},
                {'key'  : 'STAGE-CLOSED-WON',
                 'name': 'Closed Won'},
                {'key'  : 'STAGE-REGISTERED-UNVERIFIED', # UNUSED
                 'name': 'Registered Unverified'},
                {'key'  : 'STAGE-VERIFIED', # UNUSED
                 'name': 'Verified User'}]

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(Stage).filter(Stage.key == key).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_id(cls, stageid):
        session = get_session()
        try:
            return session.query(Stage).filter(Stage.id == stageid).one()
        except NoResultFound:
            return None

    @classmethod
    def get_dict(cls):
        data = {}
        session = get_session()
        for entry in session.query(Stage).all():
            data[entry.key] = entry.name
        return data

    @classmethod
    def get_stage_name(cls, stageid):
        name = cls.get_by_id(stageid).name
        return name
