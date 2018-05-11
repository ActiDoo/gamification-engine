registries = {}

class HookPointRegistry:
    def __init__(self,  single_execution=False):
        self.registrations = {}
        self.single_execution = single_execution
        self.has_been_executed = set()

    def register(self, id, fun):
        self.registrations[id]=fun

    def run_extensions(self, **kw):
        for id in self.registrations.keys():
            if (not self.single_execution) or (id not in self.has_been_executed):
                x = self.registrations[id]
                x(**kw)
                self.has_been_executed.add(id)


def get_task_registration_points_registry():
    global registries
    if "tasks_registration_points" not in registries:
        registries["tasks_registration_points"] = HookPointRegistry(single_execution=True)
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
        registries["admin_extensions"] = HookPointRegistry(single_execution=True)
    return registries["admin_extensions"]