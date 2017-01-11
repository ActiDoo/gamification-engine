class DictObjectProxy:

    def __init__(self, obj={}):
        super().__setattr__("obj",obj)

    def __getattr__(self, name):
        if not name in super().__getattribute__("obj"):
            raise AttributeError
        return super().__getattribute__("obj")[name]

    def __setattr__(self, key, value):
        super().__getattribute__("obj")[key] = value


class Proxy(object):
    def __init__(self):
        self.target = None

    def __getattr__(self, name):
        return getattr(self.target, name)

    def __setattr__(self, name, value):
        if name == "target":
            return object.__setattr__(self, name, value)
        else:
            setattr(self.target, name, value)

    def __call__(self, *args, **kwargs):
        return self.target(*args, **kwargs)
    