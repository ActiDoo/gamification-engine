# -*- coding: utf-8 -*-
import sys
import logging
import datetime
import os
import pyramid_dogpile_cache
import transaction

from gengine.base.util import dt_ago, dt_now
from sqlalchemy.sql.expression import and_
from zope.sqlalchemy.datamanager import mark_changed

from gengine.app.cache import init_caches
from pyramid.config import Configurator
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from pyramid.scripts.common import parse_vars
from sqlalchemy import engine_from_config

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())


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

    import gengine
    gengine.main({}, **settings)

    from gengine.metadata import (
        DBSession
    )
    sess = DBSession()

    import gengine.app.model as m
    import crontab

    from gengine.app.registries import get_task_registry
    enginetasks = get_task_registry().registrations

    with transaction.manager:
        mark_changed(sess, transaction.manager, True)

        tasks = sess.execute(m.t_tasks.select()).fetchall()

        for task in tasks:
            cron = task["cron"]
            if not cron:
                cron = enginetasks.get(task["task_name"]).get("default_cron", None)

            if cron:

                now = dt_now().replace(second=0)

                item = crontab.CronItem(line=cron)
                s = item.schedule(date_from=now)
                prev = s.get_next().replace(second=0)
                next = s.get_next().replace(second=0)

                execs = sess.execute(m.t_taskexecutions.select().where(and_(
                    m.t_taskexecutions.c.task_id == task["id"],
                    m.t_taskexecutions.c.canceled_at == None,
                    m.t_taskexecutions.c.finished_at == None,
                )).order_by(m.t_taskexecutions.c.planned_at.desc())).fetchall()

                found = False

                for exec in execs:

                    if exec["planned_at"] >= next:
                        # The next execution is already planned
                        found = True

                    if exec["planned_at"] <= prev and prev < dt_ago(minutes=10) and not exec["locked_at"]:
                        #  The execution is more than 10 minutes in the past and not yet locked (worker not running / overloaded)
                        if next - datetime.timedelta(minutes=10) < dt_now():
                            # The next execution is planned in less than 10 minutes, cancel the other one
                            sess.execute(
                                m.t_taskexecutions.update().values({
                                    'canceled_at': dt_now()
                                }).where({
                                    'id': exec["id"]
                                })
                            )

                    if exec["locked_at"] and exec["locked_at"] < dt_ago(hours=24):
                        # this task is running for more than 24 hours. probably crashed.... set it to canceled
                        sess.execute(
                            m.t_taskexecutions.update().values({
                                'canceled_at': dt_now()
                            }).where({
                                'id': exec["id"]
                            })
                        )

                if not found:
                    # Plan next execution
                    sess.execute(
                        m.t_taskexecutions.insert().values({
                            'task_id': task["id"],
                            'planned_at': next
                        })
                    )

        sess.flush()
        sess.commit()
