import unittest
import os
from sqlalchemy.engine import create_engine
from sqlalchemy.sql.schema import Table
from sqlalchemy.orm.scoping import scoped_session
from gengine.metadata import init_session, get_sessionmaker
from gengine.app.tests import db

class BaseDBTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if cls is BaseDBTest:
            raise unittest.SkipTest("Skip BaseTest tests, it's a base class")
        super(BaseDBTest, cls).setUpClass()

    def setUp(self):
        from gengine.app.cache import clear_all_caches
        clear_all_caches()
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
        init_session(override_session=scoped_session(get_sessionmaker(bind=self.engine)), replace=True)
        from gengine.metadata import Base
        Base.metadata.bind = self.engine

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
