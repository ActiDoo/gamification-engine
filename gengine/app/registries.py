registries = {}

class HookPointRegistry:
    def __init__(self):
        self.registrations = []

    def register(self, fun):
        self.registrations.append(fun)

    def run_extensions(self, **kw):
        for x in self.registrations:
            x(**kw)


def get_task_registration_points_registry():
    global registries
    if "tasks_registration_points" not in registries:
        registries["tasks_registration_points"] = HookPointRegistry()
    return registries["tasks_registration_points"]


def get_task_registry():
    global registries
    if "tasks" not in registries:
        from gengine.app.tasksystem import TaskRegistry
        registries["tasks"] = TaskRegistry()
    return registries["tasks"]


def get_admin_extension_registry():
    global registries
    if "admin_extensions" not in registries:
        registries["admin_extensions"] = HookPointRegistry()
    return registries["admin_extensions"]