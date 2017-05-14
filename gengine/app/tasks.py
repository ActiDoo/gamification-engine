from .tasksystem import EngineTask

@EngineTask(
    name="demo_task",
    description="print sth",
    config_scheme=None,
    default_config=None,
    default_cron="* * * * *",
    default_activated=True
)
def demo_task(config):
    print("TEST123")
    return {
        'log': None,
        'success': True
    }


