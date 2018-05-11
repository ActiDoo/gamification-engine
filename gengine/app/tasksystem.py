from collections import defaultdict
from sqlalchemy.sql.expression import and_
from zope.sqlalchemy.datamanager import mark_changed


class EngineTask(object):
    def __init__(self, name, description, config_scheme, default_config, default_cron, default_activated, *args, **kwargs):
        """Constructor just here to accept parameters for decorator"""
        self.name = name
        self.description = description
        self.config_scheme = config_scheme
        self.default_config = default_config
        self.default_cron = default_cron
        self.default_activated = default_activated
        self.args = args
        self.kwargs = kwargs

    def __call__(self, wrapped):
        """Attach the decorator with Venusian"""

        from gengine.app.registries import get_task_registry
        get_task_registry().register(self.name, wrapped, self.description, self.config_scheme, self.default_config, self.default_cron)

        if self.default_activated:
            import transaction
            from .model import t_tasks
            from ..metadata import DBSession

            if hasattr(DBSession, "target"):
                sess = DBSession()
            else:
                sess = DBSession

            with transaction.manager:

                sess.execute("LOCK TABLE tasks IN ACCESS EXCLUSIVE MODE")
                db_task = sess.execute(t_tasks.select().where(and_(
                    t_tasks.c.task_name.like(self.name),
                    t_tasks.c.is_auto_created == True,
                ))).fetchone()

                if not db_task:
                    # We are not setting config and cron, as we can get the defaults when executing

                    mark_changed(sess, transaction.manager, True)

                    sess.execute(t_tasks.insert().values({
                        'entry_name': self.name,
                        'task_name': self.name,
                        'config': None,
                        'cron': None,
                        'is_removed': False,
                        'is_manually_modified': False,
                        'is_auto_created': True,
                    }))

                    sess.flush()
                sess.commit()
        return wrapped


class TaskRegistry:
    def __init__(self):
        self.registrations = defaultdict(lambda: defaultdict(dict))

    def register(self, name, fun, description, config_scheme, default_config, default_cron):
        self.registrations[name] = {
            "fun": fun,
            "description": description,
            "config_scheme": config_scheme,
            "default_config": default_config,
            "default_cron": default_cron
        }

    def execute(self, name, config):
        if not config:
            config = self.registrations.get(name).get("default_config", None)
        return self.registrations[name]["fun"](config=config)

