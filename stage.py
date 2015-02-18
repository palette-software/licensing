from __future__ import absolute_import

from datetime import datetime
from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

class Stage(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'stage'

    id = Column(Integer, primary_key=True)

    key = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)

    defaults = [{'key' : 'stage_trial_requested',
                 'name': 'Trial Requested'},
                {'key'  : 'stage_trial_registered',
                 'name': 'Trial Registered'},
                {'key'  : 'stage_trial_notinstalled',
                 'name': 'Trial Not Installed'},
                {'key'  : 'stage_trial_noresponse',
                 'name': 'Trial No Response'},
                {'key'  : 'stage_trial_started',
                 'name': 'Trial Started'},
                {'key'  : 'stage_trial_expired',
                 'name': 'Trial Expired'},
                {'key'  : 'stage_trial_extended',
                 'name': 'Trial Extended'},
                {'key'  : 'stage_license_expired',
                 'name': 'License Expired'},
                {'key'  : 'stage_up_for_renewal',
                 'name': 'Up For Renewal'},
                {'key'  : 'stage_closed_won',
                 'name': 'Closed Won'}]

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(Stage).filter(Stage.key == key).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_id(cls, id):
        session = get_session()
        try:
            return session.query(Stage).filter(Stage.id == id).one()
        except NoResultFound:
            return None
