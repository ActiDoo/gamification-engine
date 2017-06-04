# -*- coding: utf-8 -*-
import sys
import logging

from zope.sqlalchemy.datamanager import mark_changed

from gengine.metadata import MySession

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())

import os
import pyramid_dogpile_cache
import transaction
from gengine.app.cache import init_caches
from pyramid.config import Configurator
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from pyramid.scripts.common import parse_vars
from sqlalchemy import engine_from_config

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s production.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    from gengine.base.settings import set_settings
    set_settings(settings)

    durl = os.environ.get("DATABASE_URL")  # heroku
    if durl:
        settings['sqlalchemy.url'] = durl

    murl = os.environ.get("MEMCACHED_URL")
    if murl:
        settings['urlcache_url'] = murl

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
    init_caches()

    from gengine.metadata import (
        DBSession
    )
    sess = DBSession()
    init_session(override_session=sess, replace=True)

    import gengine.app.model as m
    with transaction.manager:
        mark_changed(sess, transaction.manager, True)

        messages = sess.execute(m.t_user_messages.select().where(m.t_user_messages.c.has_been_pushed == False))
        for msg in messages:
            m.SubjectMessage.deliver(msg)
        sess.flush()
        sess.commit()
