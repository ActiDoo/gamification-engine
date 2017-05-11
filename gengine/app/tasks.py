from .tasksystem import EngineTask

@EngineTask(
    name="demo_task",
    description="print sth",
    config_scheme=None,
    default_config=None,
    default_cron=None
)
def demo_task():
    print("TEST123")


