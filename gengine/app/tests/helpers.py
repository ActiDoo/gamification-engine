import names
import random

from gengine.app.model import User, Language, Achievement,Goal, Variable, Value, t_goals, GoalProperty, GoalGoalProperty, TranslationVariable, t_goals_goalproperties
from gengine.metadata import DBSession

from gengine.app.model import UserDevice, t_user_device
from sqlalchemy import (and_)

default_gen_data = {
    "timezone" : "Europe/Berlin",
    "area" : {
        "min_lat" : 51.65,
        "max_lat" : 51.75,
        "min_lng" : 8.70,
        "max_lng" : 8.79
    },
    "country" : "DE",
    "region" : "NRW",
    "city" : "Paderborn",
    "language" : "de"
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
    "device_id" : "1234",
    "device_os" : "iOS 5",
    "app_version" : "1.1",
    "push_id" : "5678"
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
            'first_name' : names.get_first_name(),
            'last_name' : names.get_last_name()
        }

    if user_id is undefined:
        user_id = (DBSession.execute("SELECT max(id) as c FROM users").scalar() or 0) + 1

    if lat is undefined:
        lat = randrange_float(gen_data["area"]["min_lat"],gen_data["area"]["max_lat"])

    if lng is undefined:
        lng = randrange_float(gen_data["area"]["min_lng"], gen_data["area"]["max_lng"])

    if country is undefined:
        country = gen_data["country"]

    if timezone is undefined:
        timezone = gen_data["timezone"]

    if region is undefined:
        region = gen_data["region"]

    if city is undefined:
        city = gen_data["city"]

    if language is undefined:
        language = gen_data["language"]

    User.set_infos(
        user_id = user_id,
        lat = lat,
        lng = lng,
        timezone = timezone,
        country = country,
        region = region,
        city = city,
        language = language,
        groups = groups,
        friends = friends,
        additional_public_data = additional_public_data
    )
    user = DBSession.execute("SELECT country FROM users WHERE id = 1")

    return User.get_user(user_id)

def update_user( 
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
    ):

    User.set_infos(
        user_id = user_id,
        lat = lat,
        lng = lng,
        timezone = timezone,
        country = country,
        region = region,
        city = city,
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

    return User.get_user(user_id)
    

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


def create_achievement():
    achievement = Achievement()
    achievement.name = "invite_users"
    achievement.valid_start = "2016-12-16"
    achievement.valid_end = "2016-12-18"
    achievement.lat = 40.983
    achievement.lng = 41.562
    achievement.max_distance = 200000
    achievement.evaluation = "immediately"
    achievement.relevance = "friends"
    achievement.view_permission = "everyone"
    DBSession.add(achievement)

    DBSession.flush()

    achievement = achievement.get_achievement(achievement.id)
    DBSession.flush()

    return achievement


def create_goals(achievement):
    goal = Goal()
    goal.condition = """{"term": {"type": "literal", "variable": "invite_users"}}"""
    goal.goal = "5*level"
    goal.operator = "leq"
    goal.achievement_id = achievement.id
    DBSession.add(goal)
    DBSession.flush()

    goal1 = Goal()
    goal1.condition = """{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate"}}"""
    goal1.goal = "3*level"
    goal1.group_by_key = False
    goal1.operator = "geq"
    goal1.achievement_id = achievement.id
    DBSession.add(goal1)
    DBSession.flush()

    goals = DBSession.execute(t_goals.select(t_goals.c.achievement_id == achievement.id)).fetchall()
    DBSession.flush()
    print(goals)

    return goals


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
