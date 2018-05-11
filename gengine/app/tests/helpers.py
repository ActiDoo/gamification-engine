import random
import datetime

from dateutil.relativedelta import relativedelta

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
    DBSession.add(bielefeld)
    DBSession.flush()
    Subject.join_subject(subject_id=bielefeld.id, part_of_id=germany.id, join_date=default_dt())

    paderborn = create_subject(name="Paderborn", type="City")
    DBSession.add(paderborn)
    DBSession.flush()
    Subject.join_subject(subject_id=paderborn.id, part_of_id=germany.id, join_date=default_dt())

    lyon = create_subject(name="Lyon", type="City")
    DBSession.add(lyon)
    DBSession.flush()
    Subject.join_subject(subject_id=lyon.id, part_of_id=france.id, join_date=default_dt())

    junior_developer = create_subject(name="Junior Developer", type="Position")
    DBSession.add(junior_developer)

    senior_developer = create_subject(name="Senior Developer", type="Position")
    DBSession.add(senior_developer)

    project_manager = create_subject(name="Project Manager", type="Position")
    DBSession.add(project_manager)

    dev_team_bielefeld = create_subject(name="Developer Team Bielefeld", type="Team")
    DBSession.add(dev_team_bielefeld)
    DBSession.flush()
    Subject.join_subject(subject_id=dev_team_bielefeld.id, part_of_id=bielefeld.id, join_date=default_dt())

    dev_team_paderborn = create_subject(name="Developer Team Paderborn", type="Team")
    DBSession.add(dev_team_paderborn)
    DBSession.flush()
    Subject.join_subject(subject_id=dev_team_paderborn.id, part_of_id=paderborn.id, join_date=default_dt())

    dev_team_lyon = create_subject(name="Developer Team Lyon", type="Team")
    DBSession.add(dev_team_lyon)
    DBSession.flush()
    Subject.join_subject(subject_id=dev_team_lyon.id, part_of_id=lyon.id, join_date=default_dt())

    klaus = create_subject(name="Klaus", type="User")
    DBSession.add(klaus)
    DBSession.flush()
    Subject.join_subject(subject_id=klaus.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=klaus.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=klaus.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=klaus.id, part_of_id=germany.id, join_date=default_dt())

    clara = create_subject(name="Clara", type="User")
    DBSession.add(clara)
    DBSession.flush()
    Subject.join_subject(subject_id=clara.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=clara.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=clara.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=clara.id, part_of_id=germany.id, join_date=default_dt())

    manfred = create_subject(name="Manfred", type="User")
    DBSession.add(manfred)
    DBSession.flush()
    Subject.join_subject(subject_id=manfred.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=manfred.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=manfred.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=manfred.id, part_of_id=germany.id, join_date=default_dt())

    otto = create_subject(name="Otto", type="User")
    DBSession.add(otto)
    DBSession.flush()
    Subject.join_subject(subject_id=otto.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=otto.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=otto.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=otto.id, part_of_id=germany.id, join_date=default_dt())

    max = create_subject(name="Max", type="User")
    DBSession.add(max)
    DBSession.flush()
    Subject.join_subject(subject_id=max.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=max.id, part_of_id=senior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=max.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=max.id, part_of_id=germany.id, join_date=default_dt())

    ronny = create_subject(name="Ronny", type="User")
    DBSession.add(ronny)
    DBSession.flush()
    Subject.join_subject(subject_id=ronny.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=ronny.id, part_of_id=senior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=ronny.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=ronny.id, part_of_id=germany.id, join_date=default_dt())

    sonja = create_subject(name="Sonja", type="User")
    DBSession.add(sonja)
    DBSession.flush()
    Subject.join_subject(subject_id=sonja.id, part_of_id=bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=sonja.id, part_of_id=project_manager.id, join_date=default_dt())
    Subject.join_subject(subject_id=sonja.id, part_of_id=dev_team_bielefeld.id, join_date=default_dt())
    Subject.join_subject(subject_id=sonja.id, part_of_id=germany.id, join_date=default_dt())

    #Paderborn

    liam = create_subject(name="Liam", type="User")
    DBSession.add(liam)
    DBSession.flush()
    Subject.join_subject(subject_id=liam.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=liam.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=liam.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=liam.id, part_of_id=germany.id, join_date=default_dt())

    tim = create_subject(name="Tim", type="User")
    DBSession.add(tim)
    DBSession.flush()
    Subject.join_subject(subject_id=tim.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=tim.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=tim.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=tim.id, part_of_id=germany.id, join_date=default_dt())

    robin = create_subject(name="Robin", type="User")
    DBSession.add(robin)
    DBSession.flush()
    Subject.join_subject(subject_id=robin.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=robin.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=robin.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=robin.id, part_of_id=germany.id, join_date=default_dt())

    alina = create_subject(name="Alina", type="User")
    DBSession.add(alina)
    DBSession.flush()
    Subject.join_subject(subject_id=alina.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=alina.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=alina.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=alina.id, part_of_id=germany.id, join_date=default_dt())

    charlotte = create_subject(name="Charlotte", type="User")
    DBSession.add(charlotte)
    DBSession.flush()
    Subject.join_subject(subject_id=charlotte.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=charlotte.id, part_of_id=senior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=charlotte.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=charlotte.id, part_of_id=germany.id, join_date=default_dt())

    ida = create_subject(name="Ida", type="User")
    DBSession.add(ida)
    DBSession.flush()
    Subject.join_subject(subject_id=ida.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=ida.id, part_of_id=senior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=ida.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=ida.id, part_of_id=germany.id, join_date=default_dt())

    carolin = create_subject(name="Carolin", type="User")
    DBSession.add(carolin)
    DBSession.flush()
    Subject.join_subject(subject_id=carolin.id, part_of_id=paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=carolin.id, part_of_id=project_manager.id, join_date=default_dt())
    Subject.join_subject(subject_id=carolin.id, part_of_id=dev_team_paderborn.id, join_date=default_dt())
    Subject.join_subject(subject_id=carolin.id, part_of_id=germany.id, join_date=default_dt())

    #Lyon

    lola = create_subject(name="Lola", type="User")
    DBSession.add(lola)
    DBSession.flush()
    Subject.join_subject(subject_id=lola.id, part_of_id=lyon.id, join_date=default_dt())
    Subject.join_subject(subject_id=lola.id, part_of_id=junior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=lola.id, part_of_id=dev_team_lyon.id, join_date=default_dt())
    Subject.join_subject(subject_id=lola.id, part_of_id=france.id, join_date=default_dt())

    lina = create_subject(name="Lina", type="User")
    DBSession.add(lina)
    DBSession.flush()
    Subject.join_subject(subject_id=lina.id, part_of_id=lyon.id, join_date=default_dt())
    Subject.join_subject(subject_id=lina.id, part_of_id=senior_developer.id, join_date=default_dt())
    Subject.join_subject(subject_id=lina.id, part_of_id=dev_team_lyon.id, join_date=default_dt())
    Subject.join_subject(subject_id=lina.id, part_of_id=france.id, join_date=default_dt())

    ethan = create_subject(name="Ethan", type="User")
    DBSession.add(ethan)
    DBSession.flush()
    Subject.join_subject(subject_id=ethan.id, part_of_id=lyon.id, join_date=default_dt())
    Subject.join_subject(subject_id=ethan.id, part_of_id=project_manager.id, join_date=default_dt())
    Subject.join_subject(subject_id=ethan.id, part_of_id=dev_team_lyon.id, join_date=default_dt())
    Subject.join_subject(subject_id=ethan.id, part_of_id=france.id, join_date=default_dt())


def create_variables():
    invite_users = Variable(
        name="invite_users",
        increase_permission="own"
    )
    DBSession.add(invite_users)

    cycling = Variable(
        name="cycling",
        increase_permission="own"
    )
    DBSession.add(cycling)

    DBSession.flush()

def create_achievements():
    user_type = DBSession.query(SubjectType).filter_by(name="User").first()
    team_type = DBSession.query(SubjectType).filter_by(name="Team").first()
    country_type = DBSession.query(SubjectType).filter_by(name="Country").first()

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

    cyclist_of_the_month = Achievement(
        name="cyclist_of_the_month",
        hidden=False,
        evaluation="monthly",
        comparison_type="context_subject",
        player_subjecttype_id=user_type["id"],
        view_permission="everyone",
        condition="""{"term": {"type": "literal", "variable": "cycling"}}""",
        context_subjecttype_id=country_type.id,
        operator="geq"
    )
    cyclist_of_the_month.compared_subjecttypes.append(
        user_type,
        team_type
    )
    DBSession.add(cyclist_of_the_month)
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
    # Montag

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

def next_day(dt):
    return dt + relativedelta(days=1)

def next_month(dt):
    return dt + relativedelta(months=1)

def next_week(dt):
    return dt + relativedelta(weeks=1)

def last_month(dt):
    return dt - relativedelta(months=1)