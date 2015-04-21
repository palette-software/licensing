from __future__ import absolute_import

from akiri.framework.sqlalchemy import Base, get_session

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm.exc import NoResultFound

from mixin import BaseMixin

class Product(Base, BaseMixin):
    # pylint: disable=no-init
    # pylint: disable=invalid-name
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True)
    key = Column(String)
    name = Column(String, nullable=False)

    defaults = [{'key' : 'PALETTE-PRO',
                 'name': 'Palette Pro'},
                {'key'  : 'PALETTE-ENT',
                 'name': 'Palette Enterprise'}]

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
