from gengine.base.cache import create_cache

caches = {}

cache_general = None
cache_goal_evaluation = None
cache_achievement_eval = None
cache_achievements_subjects_levels = None
cache_achievements_by_subject_for_today = None
#cache_goal_statements = None
cache_translations = None

def init_caches():
    global cache_general
    cache_general = create_cache("general")

    global cache_achievement_eval
    cache_achievement_eval = create_cache("achievement_eval")

    global cache_achievements_by_subject_for_today
    cache_achievements_by_subject_for_today = create_cache("achievements_by_subject_for_today")

    global cache_achievements_subjects_levels
    cache_achievements_subjects_levels = create_cache("achievements_subjects_levels")

    global cache_translations
    cache_translations = create_cache("translations")

    # The Goal evaluation Cache is implemented as a two-level cache (persistent in db, non-persistent as dogpile)
    global cache_goal_evaluation
    cache_goal_evaluation = create_cache("goal_evaluation")

    #global cache_goal_statements
    #cache_goal_statements = create_memory_cache("goal_statements")


def clear_all_caches():
    cache_general.invalidate(hard=True)
    cache_achievement_eval.invalidate(hard=True)
    cache_achievements_by_subject_for_today.invalidate(hard=True)
    cache_achievements_subjects_levels.invalidate(hard=True)
    cache_translations.invalidate(hard=True)
    cache_goal_evaluation.invalidate(hard=True)
    #cache_goal_statements.invalidate(hard=True)
