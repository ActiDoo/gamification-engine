from .tasksystem import EngineTask

def includeme(config):

    # @EngineTask(
    #     name="demo_task",
    #     description="print sth",
    #     config_scheme=None,
    #     default_config=None,
    #     default_cron="* * * * *",
    #     default_activated=True
    # )
    # def demo_task(config):
    #     return {
    #         'log': None,
    #         'success': True
    #     }


    from gengine.app.registries import get_task_registration_points_registry
    get_task_registration_points_registry().run_extensions()


@EngineTask(
 name="import_test_data",
 description="import the test demo data",
 config_scheme=None,
 default_config=None,
 default_cron="0 0 5 31 2", # 31st feb will never exec
 default_activated=True
)
def demo_task(config):

    from gengine.app.tests.helpers import create_subjecttypes, create_subjects, create_achievements, create_variables

    create_subjecttypes()
    create_subjects()
    create_variables()
    create_achievements()

    return {
        'log': None,
        'success': True
    }
