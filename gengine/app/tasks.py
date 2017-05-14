from .tasksystem import EngineTask


def includeme(config):

    @EngineTask(
        name="demo_task",
        description="print sth",
        config_scheme=None,
        default_config=None,
        default_cron="* * * * *",
        default_activated=True
    )
    def demo_task(config):
        return {
            'log': None,
            'success': True
        }


    from gengine.app.registries import get_task_registration_points_registry
    get_task_registration_points_registry().run_extensions()
