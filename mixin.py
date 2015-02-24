from akiri.framework.sqlalchemy import get_session

import json
import os

class BaseMixin(object):

    defaults = []
    defaults_filename = None

    @classmethod
    def populate(cls):
        session = get_session()
        entry = session.query(cls).first()
        if entry:
            return
        if not cls.defaults_filename is None:
            rows = cls.populate_from_file(cls.defaults_filename)
        else:
            rows = cls.defaults
        for d in rows:
            obj = cls(**d)
            session.add(obj)
        session.commit()

    @classmethod
    def populate_from_file(cls, filename):
        path = os.path.dirname(os.path.realpath(__file__)) + "/" + filename

        with open(path, "r") as f:
            rows = json.load(f)
            return rows['RECORDS']

