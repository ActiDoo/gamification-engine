# -*- coding: utf-8 -*-
import sys
import logging

from gengine.base.util import dt_now
from sqlalchemy.sql.expression import and_, select
from zope.sqlalchemy.datamanager import mark_changed

import os
import transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from pyramid.scripts.common import parse_vars

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

    from gengine.app.registries import get_task_registry
    enginetasks = get_task_registry().registrations

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

            result = get_task_registry().execute(
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
