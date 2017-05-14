# -*- coding: utf-8 -*-
import sys
import logging

import datetime

from gengine.base.util import dt_now
from sqlalchemy.sql.expression import and_, select
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
    import crontab
    from gengine.app.tasksystem import ITaskRegistry

    config.include("gengine.app.tasksystem")
    config.scan("gengine")
    taskregistry = config.registry.getUtility(ITaskRegistry)
    enginetasks = taskregistry.registrations

    to_run = []

    with transaction.manager:
        mark_changed(sess, transaction.manager, True)

        tasks = sess.execute(
            select([
                m.t_tasks.c.entry_name,
                m.t_tasks.c.task_name,
                m.t_tasks.c.config,
                m.t_taskexecutions.c.id.label("execution_id"),
            ], from_obj=m.t_taskexecutions.join(m.t_tasks)).\
            where(and_(
                m.t_taskexecutions.c.planned_at < dt_now(),
                m.t_taskexecutions.c.canceled_at==None,
                m.t_taskexecutions.c.locked_at==None,
                m.t_taskexecutions.c.finished_at==None,
            ))
        ).fetchall()

        for task in tasks:
            if task["task_name"] in enginetasks.keys():
                to_run.append(task)

                sess.execute(
                    m.t_taskexecutions.update().values({
                        'locked_at' : dt_now()
                    }).where(
                        m.t_taskexecutions.c.id == task["execution_id"]
                    )
                )

        sess.flush()
        sess.commit()

    for task in to_run:
        with transaction.manager:
            mark_changed(sess, transaction.manager, True)

            log.info("Running task %(task_name)s (ExecutionID: %(execution_id)s)" % {
                'task_name': task["task_name"],
                'execution_id': task["execution_id"]
            })

            result = taskregistry.execute(
                name=task["task_name"],
                config=task["config"]  # execute contains fallback to default_config
            )
            logged = result.get("log", None)
            success = result.get("success", True)

            sess.execute(
                m.t_taskexecutions.update().values({
                    'finished_at': dt_now(),
                    'log': logged,
                    'success': success
                }).where(
                    m.t_taskexecutions.c.id == task["execution_id"]
                )
            )

            sess.flush()
            sess.commit()
