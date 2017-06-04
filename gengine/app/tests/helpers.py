import random
import datetime

from gengine.app.model import User, Language, Achievement,Goal, Variable, Value, t_goals, GoalProperty, GoalGoalProperty, TranslationVariable, \
    t_goals_goalproperties, t_users, GoalEvaluationCache, Reward, AchievementReward, AchievementSubject
from gengine.metadata import DBSession

from gengine.app.model import UserDevice, t_user_device
from sqlalchemy import and_, select

import logging
log = logging.getLogger(__name__)

try:
    import names
except ImportError as e:
    log.info("names not installed")

default_gen_data = {
    "timezone" : "Europe/Berlin",
    "area" : {
        "min_lat" : 51.65,
        "max_lat" : 51.75,
        "min_lng" : 8.70,
        "max_lng" : 8.79
    },
    #"country" : "DE",
    #"region" : "NRW",
    #"city" : "Paderborn",
    "language" : "de",
    "additional_public_data" : {
        "first_name" : "Matthew",
        "last_name" : "Hayden"
    }
}

alt_gen_data = {
    "timezone" : "US/Eastern",
    "area" : {
        "min_lat" : 40.680,
        "max_lat" : 40.780,
        "min_lng" : -73.89,
        "max_lng" : -73.97
    }
}

default_device_data = {
    "device_os" : "iOS 5",
    "app_version" : "1.1",
    "push_id" : "5678",
    "device_id" : "1234"
}


class Undefined():
    pass

undefined = Undefined()


def randrange_float(f1,f2):
    return random.random() * abs(f1 - f2) + min(f1,f2)


def create_user(
        user_id = undefined,
        lat = undefined,
        lng = undefined,
        country = undefined,
        region = undefined,
        city = undefined,
        timezone = undefined,
        language = undefined,
        friends = [],
        groups = [],
        additional_public_data = undefined,
        gen_data = default_gen_data
    ):
    if additional_public_data is undefined:
        additional_public_data = {
            'first_name' : 'Stefan',
            'last_name' : 'Rogers'
        }

    if user_id is undefined:
        user_id = (DBSession.execute("SELECT max(id) as c FROM users").scalar() or 0) + 1
    if lat is undefined:
        lat = randrange_float(gen_data["area"]["min_lat"],gen_data["area"]["max_lat"])

    if lng is undefined:
        lng = randrange_float(gen_data["area"]["min_lng"], gen_data["area"]["max_lng"])

    if timezone is undefined:
        timezone = gen_data["timezone"]

    #if country is undefined:
    #    country = gen_data["country"]

    #if region is undefined:
    #    region = gen_data["region"]

    #if city is undefined:
    #    city = gen_data["city"]

    if language is undefined:
        language = gen_data["language"]

    User.set_infos(
        user_id = user_id,
        lat = lat,
        lng = lng,
        timezone = timezone,
        language = language,
        groups = groups,
        friends = friends,
        additional_public_data = additional_public_data
    )

    return User.get_user(user_id)


def update_user( 
        user_id = undefined,
        lat = undefined,
        lng = undefined,
        #country = undefined,
        #region = undefined,
        #city = undefined,
        timezone = undefined,
        language = undefined,
        friends = [],
        groups = [],
        additional_public_data = undefined,
    ):

    User.set_infos(
        user_id = user_id,
        lat = lat,
        lng = lng,
        timezone = timezone,
        #country = country,
        #region = region,
        #city = city,
        language = language,
        groups = groups,
        friends = friends,
        additional_public_data = additional_public_data
    )

    return User.get_user(user_id)


def delete_user( 
        user_id = undefined,
    ):

    User.delete_user(user_id)
    users = DBSession.execute(select([t_users.c.id,])).fetchall()
    return users
    

def get_or_create_language(name):
    lang = DBSession.query(Language).filter_by(name=name).first()
    if not lang:
        lang = Language()
        lang.name = name
        DBSession.add(lang)
        DBSession.flush()
    return lang


def create_device(
        user_id=undefined,
        device_id=undefined,
        device_os=undefined,
        push_id=undefined,
        app_version=undefined,
        gen_data=default_device_data
    ):

    if push_id is undefined:
        push_id = gen_data["push_id"]

    if device_os is undefined:
        device_os = gen_data["device_os"]

    if app_version is undefined:
        app_version = gen_data["app_version"]

    if device_id is undefined:
        device_id = gen_data["device_id"]

    UserDevice.add_or_update_device(
        device_id = device_id,
        user_id = user_id,
        device_os = device_os,
        push_id = push_id,
        app_version = app_version
    )

    device = DBSession.execute(t_user_device.select().where(and_(
            t_user_device.c.device_id == device_id,
            t_user_device.c.user_id == user_id
        ))).fetchone()

    return device


def update_device(
        user_id=undefined,
        device_id=undefined,
        device_os=undefined,
        push_id=undefined,
        app_version=undefined,
    ):
    UserDevice.add_or_update_device(
        device_id=device_id,
        user_id=user_id,
        device_os=device_os,
        push_id=push_id,
        app_version=app_version
    )

    device = DBSession.execute(t_user_device.select().where(and_(
        t_user_device.c.device_id == device_id,
        t_user_device.c.user_id == user_id
    ))).fetchone()

    return device


def create_achievement(
        achievement_name = undefined,
        achievement_valid_start = undefined,
        achievement_valid_end = undefined,
        achievement_lat = undefined,
        achievement_lng = undefined,
        achievement_max_distance = undefined,
        achievement_evaluation = undefined,
        achievement_relevance = undefined,
        achievement_maxlevel = undefined,
        achievement_view_permission = undefined,
        achievement_evaluation_shift = undefined,
        achievement_evaluation_timezone = undefined,
    ):
    achievement = Achievement()

    if achievement_name is undefined:
        achievement.name = "invite_users_achievement"
    else:
        achievement.name = achievement_name

    if achievement_valid_start is undefined:
        achievement.valid_start = "2016-12-16"
    else:
        achievement.valid_start = achievement_valid_start

    if achievement_valid_end is undefined:
        achievement.valid_end = datetime.date.today()
    else:
        achievement.valid_end = achievement_valid_end

    if achievement_lat is undefined:
        achievement.lat = 40.983
    else:
        achievement.lat = achievement_lat

    if achievement_lng is undefined:
        achievement.lng = 41.562
    else:
        achievement.lng = achievement_lng

    if achievement_max_distance is undefined:
        achievement.max_distance = 20000
    else:
        achievement.max_distance = achievement_max_distance

    if achievement_evaluation is undefined:
        achievement.evaluation = "immediately"
    else:
        achievement.evaluation = achievement_evaluation

    if achievement_relevance is undefined:
        achievement.relevance = "friends"
    else:
        achievement.relevance = achievement_relevance

    if achievement_maxlevel is undefined:
        achievement.maxlevel = 3
    else:
        achievement.maxlevel = achievement_maxlevel

    if achievement_view_permission is undefined:
        achievement.view_permission = "everyone"
    else:
        achievement.view_permission = achievement_view_permission

    if achievement_evaluation_shift is undefined:
        achievement.evaluation_shift = None
    else:
        achievement.evaluation_shift = achievement_evaluation_shift

    if achievement_evaluation_shift is undefined:
        achievement.evaluation_timezone = "UTC"
    else:
        achievement.evaluation_timezone = achievement_evaluation_timezone

    DBSession.add(achievement)
    DBSession.flush()

    return achievement


def create_goals(
        achievement = undefined,
        goal_condition = undefined,
        goal_goal = undefined,
        goal_operator = undefined,
        goal_group_by_key = undefined,
        goal_name = undefined
    ):
    goal = Goal()
    if achievement["name"] is "invite_users_achievement":

        if goal_condition is undefined:
            goal.condition = """{"term": {"type": "literal", "variable": "invite_users"}}"""
        else:
            goal.condition = goal_condition

        if goal_goal is undefined:
            goal.goal = "5*level"
        else:
            goal.goal = goal_goal

        if goal_operator is undefined:
            goal.operator = "geq"
        else:
            goal.operator = goal_operator

        if goal_group_by_key is undefined:
            goal.group_by_key = False
        else:
            goal.group_by_key = goal_group_by_key

        if goal_name is undefined:
            goal.name = "goal_invite_users"
        else:
            goal.name = goal_name

        goal.achievement_id = achievement.id
        DBSession.add(goal)
        DBSession.flush()

    if achievement["name"] is "participate_achievement":

        if goal_condition is undefined:
            goal.condition = """{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate"}}"""
        else:
            goal.condition = goal_condition

        if goal_goal is undefined:
            goal.goal = "3*level"
        else:
            goal.goal = goal_goal

        if goal_operator is undefined:
            goal.operator = "geq"
        else:
            goal.operator = goal_operator

        if goal_group_by_key is undefined:
            goal.group_by_key = True
        else:
            goal.group_by_key = goal_group_by_key

        if goal_name is undefined:
            goal.name = "goal_participate"
        else:
            goal.name = goal_name

        goal.achievement_id = achievement.id
        DBSession.add(goal)
        DBSession.flush()

    return goal


def create_goal_properties(goal_id):

    goal_property = GoalProperty()
    goal_property.name = "participate"
    goal_property.is_variable = True
    DBSession.add(goal_property)
    DBSession.flush()

    translation_variable = TranslationVariable()
    translation_variable.name = "invite_users_goal_name"
    DBSession.add(translation_variable)
    DBSession.flush()

    goals_goal_property = GoalGoalProperty()
    goals_goal_property.goal_id = goal_id
    goals_goal_property.property_id = goal_property.id
    goals_goal_property.value = "7"
    goals_goal_property.value_translation_id = translation_variable.id
    goals_goal_property.from_level = 2
    DBSession.add(goals_goal_property)
    DBSession.flush()

    goals_goal_property_result = DBSession.execute(t_goals_goalproperties.select().where(t_goals_goalproperties.c.goal_id == goal_id)).fetchone()

    return goals_goal_property_result


def create_achievement_rewards(achievement):
    reward = Reward()
    reward.name = "badge"
    DBSession.add(reward)
    DBSession.flush()

    achievement_reward = AchievementReward()
    achievement_reward.achievement_id = achievement.id
    achievement_reward.reward_id = reward.id
    achievement_reward.value = "https://www.gamification-software.com/img/trophy_{level1}.png"
    achievement_reward.from_level = achievement.maxlevel
    DBSession.add(achievement_reward)
    DBSession.flush()

    return achievement_reward


def create_achievement_user(user, achievement, achievement_date, level):
    achievement_user = AchievementSubject()
    achievement_user.user_id = user.id
    achievement_user.achievement_id = achievement.id
    achievement_user.achievement_date = achievement_date
    achievement_user.level = level
    DBSession.add(achievement_user)
    DBSession.flush()

    return achievement_user


def create_goal_evaluation_cache(
        goal_id ,
        gec_achievement_date,
        gec_user_id,
        gec_achieved = undefined,
        gec_value = undefined,
    ):
    goal_evaluation_cache = GoalEvaluationCache()

    if gec_achieved is undefined:
        goal_evaluation_cache.gec_achieved = True
    else:
        goal_evaluation_cache.gec_achieved = gec_achieved

    if gec_value is undefined:
        goal_evaluation_cache.gec_value = 20.0
    else:
        goal_evaluation_cache.gec_value = gec_value

    goal_evaluation_cache.goal_id = goal_id
    goal_evaluation_cache.achievement_date = gec_achievement_date
    goal_evaluation_cache.user_id = gec_user_id
    goal_evaluation_cache.achieved = gec_achieved
    goal_evaluation_cache.value = gec_value
    DBSession.add(goal_evaluation_cache)
    DBSession.flush()

    return goal_evaluation_cache


def create_variable(
        variable_name = undefined,
        variable_group = undefined,
    ):
    variable = Variable()
    variable.name = variable_name
    variable.group = variable_group
    DBSession.add(variable)
    DBSession.flush()

    return variable


def create_value(
        user_id=undefined,
        variable_id=undefined,
        var_value=undefined,
        key="",
    ):

    value = Value()
    value.user_id = user_id
    value.variable_id = variable_id
    value.value = var_value
    value.key = key
    DBSession.add(value)
    DBSession.flush()

    return value
