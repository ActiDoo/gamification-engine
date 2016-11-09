import warnings
from dogpile.cache import make_region
from pyramid_dogpile_cache import get_region

force_redis = None

def setup_redis_cache(host,port,db):
    """ This is used to override all caching settings in the ini file. Needed for Testing. """
    global force_redis
    force_redis = {
        'host': host,
        'port': port,
        'db': db,
        'redis_expiration_time': 60 * 60 * 2,  # 2 hours
        'distributed_lock': True
    }


def my_key_mangler(prefix):
    def s(o):
        if type(o) == dict:
            return "_".join(["%s=%s" % (str(k), str(v)) for k, v in o.items()])
        if type(o) == tuple:
            return "_".join([str(v) for v in o])
        if type(o) == list:
            return "_".join([str(v) for v in o])
        else:
            return str(o)

    def generate_key(key):
        ret = ""
        ret += prefix + s(key).replace(" ", "")
        return ret

    return generate_key


def create_cache(name):
    ch = None

    if force_redis:
        ch = make_region().configure(
            'dogpile.cache.redis',
            arguments=force_redis
        )
    else:
        try:
            ch = get_region(name)
        except:
            ch = make_region().configure('dogpile.cache.memory')
            warnings.warn("Warning: cache objects are in memory, are you creating docs?")

    ch.key_mangler = my_key_mangler(name)
    
    return ch
