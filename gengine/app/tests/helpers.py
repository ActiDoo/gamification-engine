import random
import datetime

from gengine.app.model import Subject, Language, Achievement, Variable, Value, TranslationVariable, \
    t_subjects, Reward, AchievementReward, SubjectType, t_subjecttypes, SubjectDevice, t_subject_device, \
    AchievementProperty
from gengine.metadata import DBSession
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


def create_subjecttypes():
    subjecttype_country = SubjectType(name="Country")
    DBSession.add(subjecttype_country)

    subjecttype_city = SubjectType(name="City")
    subjecttype_city.part_of_types.append(subjecttype_country)
    DBSession.add(subjecttype_city)

    subjecttype_position = SubjectType(name="Position")
    DBSession.add(subjecttype_position)

    subjecttype_team = SubjectType(name="Team")
    subjecttype_team.part_of_types.append(subjecttype_city)
    DBSession.add(subjecttype_team)

    subjecttype_user = SubjectType(name="User")
    subjecttype_user.part_of_types.append(subjecttype_city)
    subjecttype_user.part_of_types.append(subjecttype_team)
    subjecttype_user.part_of_types.append(subjecttype_position)
    DBSession.add(subjecttype_team)
    DBSession.flush()

def get_user_subjecttype():
    return DBSession.query(SubjectType).filter_by(name="User").first()

def create_subjects():
    germany = create_subject(name="Germany", type="Country")
    DBSession.add(germany)

    france = create_subject(name="France", type="Country")
    DBSession.add(france)

    bielefeld = create_subject(name="Bielefeld", type="City")
    bielefeld.part_of_subjects.append(germany)
    DBSession.add(bielefeld)

    paderborn = create_subject(name="Paderborn", type="City")
    paderborn.part_of_subjects.append(germany)
    DBSession.add(paderborn)

    lyon = create_subject(name="Lyon", type="City")
    lyon.part_of_subjects.append(france)
    DBSession.add(lyon)

    junior_developer = create_subject(name="Junior Developer", type="Position")
    DBSession.add(junior_developer)

    senior_developer = create_subject(name="Senior Developer", type="Position")
    DBSession.add(senior_developer)

    project_manager = create_subject(name="Project Manager", type="Position")
    DBSession.add(project_manager)

    dev_team_bielefeld = create_subject(name="Developer Team Bielefeld", type="Team")
    dev_team_bielefeld.part_of_subjects.append(bielefeld)
    DBSession.add(dev_team_bielefeld)

    dev_team_paderborn = create_subject(name="Developer Team Paderborn", type="Team")
    dev_team_bielefeld.part_of_subjects.append(paderborn)
    DBSession.add(dev_team_paderborn)

    dev_team_lyon = create_subject(name="Developer Team Lyon", type="Team")
    dev_team_bielefeld.part_of_subjects.append(lyon)
    DBSession.add(dev_team_lyon)

    klaus = create_subject(name="Klaus", type="User")
    klaus.part_of_subjects.append(bielefeld)
    klaus.part_of_subjects.append(junior_developer)
    klaus.part_of_subjects.append(dev_team_bielefeld)
    klaus.part_of_subjects.append(germany)
    DBSession.add(klaus)

    clara = create_subject(name="Clara", type="User")
    clara.part_of_subjects.append(bielefeld)
    clara.part_of_subjects.append(junior_developer)
    clara.part_of_subjects.append(dev_team_bielefeld)
    clara.part_of_subjects.append(germany)
    DBSession.add(clara)

    manfred = create_subject(name="Manfred", type="User")
    manfred.part_of_subjects.append(bielefeld)
    manfred.part_of_subjects.append(junior_developer)
    manfred.part_of_subjects.append(dev_team_bielefeld)
    manfred.part_of_subjects.append(germany)
    DBSession.add(manfred)

    otto = create_subject(name="Otto", type="User")
    otto.part_of_subjects.append(bielefeld)
    otto.part_of_subjects.append(junior_developer)
    otto.part_of_subjects.append(dev_team_bielefeld)
    otto.part_of_subjects.append(germany)
    DBSession.add(otto)

    max = create_subject(name="Max", type="User")
    max.part_of_subjects.append(bielefeld)
    max.part_of_subjects.append(senior_developer)
    max.part_of_subjects.append(dev_team_bielefeld)
    max.part_of_subjects.append(germany)
    DBSession.add(max)

    ronny = create_subject(name="Ronny", type="User")
    ronny.part_of_subjects.append(bielefeld)
    ronny.part_of_subjects.append(senior_developer)
    ronny.part_of_subjects.append(dev_team_bielefeld)
    ronny.part_of_subjects.append(germany)
    DBSession.add(ronny)

    sonja = create_subject(name="Sonja", type="User")
    sonja.part_of_subjects.append(bielefeld)
    sonja.part_of_subjects.append(project_manager)
    sonja.part_of_subjects.append(dev_team_bielefeld)
    sonja.part_of_subjects.append(germany)
    DBSession.add(sonja)

    #Paderborn

    liam = create_subject(name="Liam", type="User")
    liam.part_of_subjects.append(paderborn)
    liam.part_of_subjects.append(junior_developer)
    liam.part_of_subjects.append(dev_team_paderborn)
    liam.part_of_subjects.append(germany)
    DBSession.add(liam)

    tim = create_subject(name="Tim", type="User")
    tim.part_of_subjects.append(paderborn)
    tim.part_of_subjects.append(junior_developer)
    tim.part_of_subjects.append(dev_team_paderborn)
    tim.part_of_subjects.append(germany)
    DBSession.add(tim)

    robin = create_subject(name="Robin", type="User")
    robin.part_of_subjects.append(paderborn)
    robin.part_of_subjects.append(junior_developer)
    robin.part_of_subjects.append(dev_team_paderborn)
    robin.part_of_subjects.append(germany)
    DBSession.add(robin)

    alina = create_subject(name="Alina", type="User")
    alina.part_of_subjects.append(paderborn)
    alina.part_of_subjects.append(junior_developer)
    alina.part_of_subjects.append(dev_team_paderborn)
    alina.part_of_subjects.append(germany)
    DBSession.add(alina)

    charlotte = create_subject(name="Charlotte", type="User")
    charlotte.part_of_subjects.append(paderborn)
    charlotte.part_of_subjects.append(senior_developer)
    charlotte.part_of_subjects.append(dev_team_paderborn)
    charlotte.part_of_subjects.append(germany)
    DBSession.add(charlotte)

    ida = create_subject(name="Ida", type="User")
    ida.part_of_subjects.append(paderborn)
    ida.part_of_subjects.append(senior_developer)
    ida.part_of_subjects.append(dev_team_paderborn)
    ida.part_of_subjects.append(germany)
    DBSession.add(ida)

    carolin = create_subject(name="Carolin", type="User")
    carolin.part_of_subjects.append(paderborn)
    carolin.part_of_subjects.append(project_manager)
    carolin.part_of_subjects.append(dev_team_paderborn)
    carolin.part_of_subjects.append(germany)
    DBSession.add(sonja)

    #Lyon

    lola = create_subject(name="Lola", type="User")
    lola.part_of_subjects.append(lyon)
    lola.part_of_subjects.append(junior_developer)
    lola.part_of_subjects.append(dev_team_lyon)
    lola.part_of_subjects.append(france)
    DBSession.add(lola)

    lina = create_subject(name="Lina", type="User")
    lina.part_of_subjects.append(lyon)
    lina.part_of_subjects.append(senior_developer)
    lina.part_of_subjects.append(dev_team_lyon)
    lina.part_of_subjects.append(france)
    DBSession.add(lina)

    ethan = create_subject(name="Ethan", type="User")
    ethan.part_of_subjects.append(lyon)
    ethan.part_of_subjects.append(project_manager)
    ethan.part_of_subjects.append(dev_team_lyon)
    ethan.part_of_subjects.append(france)
    DBSession.add(ethan)
    DBSession.flush()

def create_variables():
    invite_users = Variable(
        name="invite_users",
        increase_permission="own"
    )
    DBSession.add(invite_users)
    DBSession.flush()

def create_achievements():
    user_type = DBSession.query(SubjectType).filter_by(name="User").first()
    invite_users = Achievement(
        name="invite_users",
        maxlevel=100,
        hidden=False,
        evaluation="immediately",
        comparison_type="none",
        player_subjecttype_id=user_type["id"],
        view_permission="own",
        condition="""{"term": {"type": "literal", "variable": "invite_users"}}""",
        goal="3*level",
        operator="geq"
    )
    DBSession.add(invite_users)
    DBSession.flush()
    #goal.condition = """"""
    #goal.condition = """{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate"}}"""


def create_subject(
        name,
        type,
        lat=None,
        lng=None,
        timezone=None,
        language=None,
        additional_public_data={},
    ):

    type_obj = DBSession.query(SubjectType).filter_by(name=type).first()
    language_obj = get_or_create_language(name=language) if language else None

    subject = Subject()
    subject.name = name
    subject.lat = lat
    subject.lng = lng
    subject.timezone = timezone
    subject.language = language_obj
    subject.additional_public_data = additional_public_data
    subject.type = type_obj
    DBSession.add(subject)
    return subject

def get_or_create_language(name):
    lang = DBSession.query(Language).filter_by(name=name).first()
    if not lang:
        lang = Language()
        lang.name = name
        DBSession.add(lang)
        DBSession.flush()
    return lang

def create_device(
        subject_id=undefined,
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

    SubjectDevice.add_or_update_device(
        device_id = device_id,
        subject_id = subject_id,
        device_os = device_os,
        push_id = push_id,
        app_version = app_version
    )

    device = DBSession.execute(t_subject_device.select().where(and_(
        t_subject_device.c.device_id == device_id,
        t_subject_device.c.subject_id == subject_id
    ))).fetchone()

    return device

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

def create_variable(name, increase_permission="admin"):
    variable = Variable()
    variable.name = name
    variable.increase_permission = increase_permission
    DBSession.add(variable)
    DBSession.flush()
    return variable

def default_dt():
    import datetime
    import pytz

    dt = datetime.datetime(
        year=2017,
        month=5,
        day=1,
        hour=10,
        minute=0,
        second=0,
        tzinfo=pytz.UTC
    )

    return dt