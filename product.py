from __future__ import absolute_import

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

PRO_KEY = 'PALETTE-PRO'
ENT_KEY = 'PALETTE-ENT'
INS_KEY = 'INSIGHT'

class Product(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'product'

    PRO_KEY = PRO_KEY
    ENT_KEY = ENT_KEY
    INS_KEY = INS_KEY

    id = Column(Integer, primary_key=True)
    key = Column(String)
    name = Column(String, nullable=False)

    defaults = [{'key' : PRO_KEY,
                 'name': 'Palette Pro for Tableau Server'},
                {'key'  : ENT_KEY,
                 'name': 'Palette Enterprise for Tableau Server'},
                {'key' : INS_KEY,
                 'name': 'Palette Insight'}]

    @classmethod
    def get_by_id(cls, rowid):
        session = get_session()
        try:
            return session.query(Product).filter(Product.id == rowid).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_key(cls, key):
        session = get_session()
        try:
            return session.query(Product).filter(Product.key == key).one()
        except NoResultFound:
            return None

    @classmethod
    def get_dict(cls):
        data = {}
        session = get_session()
        for entry in session.query(Product).all():
            data[entry.key] = entry.name
        return data
