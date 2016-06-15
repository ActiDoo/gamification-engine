class DictObjectProxy:

    def __init__(self, obj={}):
        super().__setattr__("obj",obj)

    def __getattr__(self, name):
        if not name in super().__getattribute__("obj"):
            raise AttributeError
        return super().__getattribute__("obj")[name]

    def __setattr__(self, key, value):
        super().__getattribute__("obj")[key] = value
