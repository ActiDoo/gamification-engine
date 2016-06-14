import warnings
from dogpile.cache import make_region
from pyramid_dogpile_cache import get_region


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
        return prefix + s(key).replace(" ", "")

    return generate_key


def create_cache(name):
    ch = None

    try:
        ch = get_region(name)
        # The Goal evaluation Cache is implemented as a two-level cache (persistent in db, non-persistent as dogpile)
    except:
        ch = make_region().configure('dogpile.cache.memory')
        warnings.warn("Warning: cache objects are in memory, are you creating docs?")

    ch.key_mangler = my_key_mangler(name)
    
    return ch



cache_general = create_cache("general")
cache_achievement_eval = create_cache("achievement_eval")
cache_achievements_by_user_for_today = create_cache("achievements_by_user_for_today")
cache_achievements_users_levels = create_cache("achievements_users_levels")
cache_translations = create_cache("translations")
# The Goal evaluation Cache is implemented as a two-level cache (persistent in db, non-persistent as dogpile)
cache_goal_evaluation = create_cache("goal_evaluation")
cache_goal_statements = create_cache("goal_statements")


def clear_all_caches():
    cache_achievement_eval.invalidate(hard=True)
    cache_achievements_by_user_for_today.invalidate(hard=True)
    cache_translations.invalidate(hard=True)
    cache_general.invalidate(hard=True)
    cache_goal_evaluation.invalidate(hard=True)
    cache_goal_statements.invalidate(hard=True)
    invalidate_all_mc()


# URL Cache

# -*- coding: utf-8 -*-
from pymemcache.client import Client

host = "localhost"
port = 11211
urlprefix = ""
is_active = True
urlcacheid = "gengine"


def setup_urlcache(prefix, url, active, id):
    global urlprefix, host, port, is_active, urlcacheid
    urlprefix = prefix
    host, port = url.split(":")
    port = int(port)
    is_active = active
    urlcacheid = id


def __build_key(key):
    return "::URL_CACHE::" + str(urlcacheid) + "::" + urlprefix + str(key)


def get_or_set(key, generator):
    if is_active:
        client = Client((host, port))
        key = __build_key(key)
        result = client.get(key)
        if not result:
            result = generator()
            client.set(key, result)
        client.quit()
        return result
    else:
        return generator()


def set_value(key, value):
    if is_active:
        client = Client((host, port))
        key = __build_key(key)
        client.set(key, value)
        client.quit()


def invalidate(key):
    if is_active:
        key = __build_key(key)
        client = Client((host, port))
        client.delete(key)
        client.quit()


def invalidate_all_mc():
    if is_active:
        client = Client((host, port))
        client.flush_all()
        client.quit()