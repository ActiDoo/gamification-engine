# -*- coding: utf-8 -*-
import sys

import os
import pyramid_dogpile_cache

from pyramid.config import Configurator
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from pyramid.scripts.common import parse_vars
from sqlalchemy import engine_from_config

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <message> [var=value]\n'
          '(example: "%s production.ini new_table_xy_created")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 3:
        usage(argv)
    config_uri = argv[1]
    message = argv[2]
    options = parse_vars(argv[3:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    durl = os.environ.get("DATABASE_URL")  # heroku
    if durl:
        settings['sqlalchemy.url'] = durl

    murl = os.environ.get("MEMCACHED_URL")
    if murl:
        settings['urlcache_url'] = murl

    revision(settings, message, options)


def revision(settings, message, options):
    engine = engine_from_config(settings, 'sqlalchemy.')

    config = Configurator(settings=settings)
    pyramid_dogpile_cache.includeme(config)

    from gengine.metadata import (
        init_session,
        init_declarative_base,
        init_db
    )
    init_session()
    init_declarative_base()
    init_db(engine)

    from gengine.app.cache import init_caches
    init_caches()

    from gengine.metadata import (
        Base,
    )

    if options.get("reset_db", False):
        Base.metadata.drop_all(engine)
        engine.execute("DROP SCHEMA IF EXISTS public CASCADE")

    engine.execute("CREATE SCHEMA IF NOT EXISTS public")

    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(attributes={
        'engine': engine,
        'schema': 'public'
    })
    script_location = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'app/alembic'
    )
    alembic_cfg.set_main_option("script_location", script_location)

    command.revision(alembic_cfg,message,True)

    engine.dispose()

if __name__ == '__main__':
    main()