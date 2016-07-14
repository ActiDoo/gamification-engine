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
        ret = ""
        ret += prefix + s(key).replace(" ", "")
        return ret

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
