from __future__ import with_statement

from logging.config import fileConfig

import os
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:
    fileConfig(config.config_file_name)

overrides = {}

durl = os.environ.get("DATABASE_URL") #heroku
if durl:
    config.set_main_option('sqlalchemy.url',durl)

# add your model's MetaData object here
# for 'autogenerate' support
from gengine.metadata import init_session,init_declarative_base
init_session()
init_declarative_base()

from gengine.metadata import Base
target_metadata = Base.metadata

# target_metadata = None

from gengine.app.model import *

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    engine = config.attributes["engine"]

    schema = config.attributes["schema"]

    #connectable = create_engine(url, poolclass=pool.NullPool)

    with engine.connect() as connection:

        connection.execute("SET search_path TO "+schema)

        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
