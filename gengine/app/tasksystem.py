from collections import defaultdict

import venusian
import zope.interface

from sqlalchemy.sql.expression import and_
from zope.interface.declarations import implementer

# Registry, Config, Decorator:
from zope.sqlalchemy.datamanager import mark_changed


def includeme(config):
    config.registry.registerUtility(TaskRegistry())

class EngineTask(object):
    def __init__(self, name, description, config_scheme, default_config, default_cron, *args, **kwargs):
        """Constructor just here to accept parameters for decorator"""
        self.name = name
        self.description = description
        self.config_scheme = config_scheme
        self.default_config = default_config
        self.default_cron = default_cron
        self.args = args
        self.kwargs = kwargs

    def __call__(self, wrapped):
        """Attach the decorator with Venusian"""
        args = self.args
        kwargs = self.kwargs

        def callback(scanner, _name, wrapped):
            """Register a view; called on config.scan"""
            config = scanner.config

            registry = config.registry
            registry.getUtility(ITaskRegistry).register(self.name, self.description, self.config_scheme, self.default_config, self.default_cron)

            import transaction
            from .model import t_tasks
            from ..metadata import DBSession

            sess = DBSession.target()
            with transaction.manager:

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
                        'is_user_modified': False,
                        'is_auto_created': True,
                    }))

                    sess.flush()
                sess.commit()

        info = venusian.attach(wrapped, callback)

        if info.scope == 'class':  # pylint:disable=E1101
            # if the decorator was attached to a method in a class, or
            # otherwise executed at class scope, we need to set an
            # 'attr' into the settings if one isn't already in there
            if kwargs.get('attr') is None:
                kwargs['attr'] = wrapped.__name__
        return wrapped


class ITaskRegistry(zope.interface.Interface):
    registrations = zope.interface.Attribute("""blahblah""")

    def register(name, description, config_scheme, default_config, default_cron):
        """bar blah blah"""


@implementer(ITaskRegistry)
class TaskRegistry:
    def __init__(self):
        self.registrations = defaultdict(lambda: defaultdict(dict))

    def register(self, name, description, config_scheme, default_config, default_cron):
        self.registrations[name] = {
            "description": description,
            "config_scheme": config_scheme,
            "default_config": default_config,
            "default_cron": default_cron
        }