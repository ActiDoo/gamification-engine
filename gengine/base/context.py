import threading

from gengine.base.util import DictObjectProxy

_local = threading.local()

def get_context():
    if not hasattr(_local, "context"):
        _local.context = DictObjectProxy()
    return _local.context

def reset_context():
    _local.context = DictObjectProxy()