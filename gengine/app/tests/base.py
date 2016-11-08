import unittest
import os
from sqlalchemy.engine import create_engine
from sqlalchemy.sql.schema import Table
from gengine.metadata import init_db
from gengine.app.tests import db as db

class BaseDBTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if cls is BaseDBTest:
            raise unittest.SkipTest("Skip BaseTest tests, it's a base class")
        super(BaseDBTest, cls).setUpClass()

    def setUp(self):
        self.db = db.db()
        dsn = self.db.dsn()
        self.engine =  create_engine(
            "postgresql://%(user)s@%(host)s:%(port)s/%(database)s" % {
                "user" : dsn["user"],
                "host": dsn["host"],
                "port": dsn["port"],
                "database": dsn["database"],
            }
        )
        init_db(self.engine)

        from gengine.metadata import Base

        Base.metadata.drop_all(self.engine)
        self.engine.execute("DROP SCHEMA IF EXISTS public CASCADE")
        self.engine.execute("CREATE SCHEMA IF NOT EXISTS public")

        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(attributes={
            'engine': self.engine,
            'schema': 'public'
        })
        script_location = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'app/alembic'
        )
        alembic_cfg.set_main_option("script_location", script_location)

        from gengine.app import model

        tables = [t for name, t in model.__dict__.items() if isinstance(t, Table)]
        Base.metadata.create_all(self.engine, tables=tables)

        command.stamp(alembic_cfg, "head")

    def tearDown(self):
        self.db.stop()

