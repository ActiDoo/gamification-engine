# -*- coding: utf-8 -*-
import sys

import os

import pyramid_dogpile_cache
import transaction
from pyramid.config import Configurator
from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )
from pyramid.scripts.common import parse_vars
from sqlalchemy import engine_from_config
from sqlalchemy.sql.expression import and_, select
from sqlalchemy.sql.schema import Table

from gengine.app.cache import init_caches
from gengine.app.permissions import perm_global_delete_subject, perm_global_increase_value, perm_global_manage_subjects, \
    perm_global_access_admin_ui, perm_global_read_messages, perm_global_register_device, yield_all_perms
from gengine.base.model import exists_by_expr


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s production.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    
    durl = os.environ.get("DATABASE_URL") #heroku
    if durl:
        settings['sqlalchemy.url']=durl

    murl = os.environ.get("MEMCACHED_URL")
    if murl:
        settings['urlcache_url']=murl

    initialize(settings,options)

def initialize(settings,options):
    engine = engine_from_config(settings, 'sqlalchemy.')
    
    config = Configurator(settings=settings)
    pyramid_dogpile_cache.includeme(config)
    
    from gengine.metadata import (
        init_session,
        init_declarative_base,
        init_db
    )
    init_caches()
    init_session()
    init_declarative_base()
    init_db(engine)
    
    from gengine.metadata import (
        Base,
        DBSession
    )

    if options.get("reset_db",False):
        Base.metadata.drop_all(engine)
        engine.execute("DROP SCHEMA IF EXISTS public CASCADE")

    engine.execute("CREATE SCHEMA IF NOT EXISTS public")

    from alembic.config import Config
    from alembic import command
    from alembic.runtime.migration import MigrationContext

    alembic_cfg = Config(attributes={
        'engine' : engine,
        'schema' : 'public'
    })
    script_location = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'app/alembic'
    )
    alembic_cfg.set_main_option("script_location", script_location)

    context = MigrationContext.configure(engine.connect())
    current_rev = context.get_current_revision()

    if not current_rev:
        #init
        from gengine.app import model

        tables = [t for name, t in model.__dict__.items() if isinstance(t, Table)]
        Base.metadata.create_all(engine, tables=tables)

        command.stamp(alembic_cfg, "head")

        if options.get("populate_demo", False):
            populate_demo(DBSession)

        admin_user = options.get("admin_user", False)
        admin_password = options.get("admin_password", False)

        if admin_user and admin_password:
            create_user(DBSession=DBSession, user=admin_user, password=admin_password)
    else:
        #upgrade
        command.upgrade(alembic_cfg,'head')

    engine.dispose()


def get_or_create_role(DBSession, name):
    from gengine.app.model import AuthRole

    auth_role = DBSession.query(AuthRole).filter_by(name=name).first()
    if not auth_role:
        auth_role = AuthRole(name=name)
        DBSession.add(auth_role)
    return auth_role


def create_user(DBSession, user, password):
    from gengine.app.model import (
        AuthUser,
        Subject,
        AuthRole,
        AuthRolePermission,
        SubjectType,
        t_auth_roles_permissions
    )
    with transaction.manager:
        subjecttype_user = DBSession.query(SubjectType).filter_by(name="User").first()
        if not subjecttype_user:
            subjecttype_user = SubjectType(name="User")
            DBSession.add(subjecttype_user)

        existing = DBSession.query(AuthUser).filter_by(email=user).first()
        DBSession.flush()
        if not existing:
            user1 = Subject(lat=10, lng=50, timezone="Europe/Berlin", subjecttype_id=subjecttype_user.id)
            DBSession.add(user1)
            DBSession.flush()

            auth_user = AuthUser(subject=user1, email=user, password=password, active=True)
            DBSession.add(auth_user)

            auth_role = get_or_create_role(DBSession=DBSession, name="Global Admin")

            for perm in yield_all_perms():
                if not exists_by_expr(t_auth_roles_permissions, and_(
                    t_auth_roles_permissions.c.auth_role_id == auth_role.id,
                    t_auth_roles_permissions.c.name == perm[0]
                )):
                    DBSession.add(AuthRolePermission(role=auth_role, name=perm[0]))

            auth_user.roles.append(auth_role)

            DBSession.add(auth_user)

            DBSession.flush()

def populate_demo(DBSession):

    from gengine.app.model import (
        Achievement,
        AchievementCategory,
        Variable,
        Subject,
        Language,
        TranslationVariable,
        Translation,
        Reward,
        AchievementProperty,
        AchievementAchievementProperty,
        AchievementReward,
        AuthUser,
        AuthRole,
        AuthRolePermission,
        SubjectType,
        t_auth_roles_permissions
    )

    def add_translation_variable(name):
        t = TranslationVariable(name=name)
        DBSession.add(t)
        return t

    def add_translation(variable, lang, text):
        tr = Translation(translationvariable=variable, text=text, language=lang)
        DBSession.add(tr)
        return tr

    with transaction.manager:
        subjecttype_country = SubjectType(name="Country")
        DBSession.add(subjecttype_country)

        subjecttype_region = SubjectType(name="Region")
        subjecttype_region.part_of_types.append(subjecttype_country)
        DBSession.add(subjecttype_region)

        subjecttype_city = SubjectType(name="City")
        subjecttype_city.part_of_types.append(subjecttype_region)
        DBSession.add(subjecttype_city)

        subjecttype_position = SubjectType(name="Position")
        DBSession.add(subjecttype_position)

        subjecttype_team = SubjectType(name="Team")
        DBSession.add(subjecttype_team)

        subjecttype_user = DBSession.query(SubjectType).filter_by(name="User").first()
        if not subjecttype_user:
            subjecttype_user = SubjectType(name="User")
            DBSession.add(subjecttype_user)
        subjecttype_user.part_of_types.append(subjecttype_city)
        subjecttype_user.part_of_types.append(subjecttype_team)
        subjecttype_user.part_of_types.append(subjecttype_position)
        DBSession.add(subjecttype_user)

        subject_germany = Subject(type=subjecttype_country, name="Germany")
        DBSession.add(subject_germany)
        subject_france = Subject(type=subjecttype_country, name="France")
        DBSession.add(subject_france)
        subject_india = Subject(type=subjecttype_country, name="India")
        DBSession.add(subject_india)

        subject_germany_north = Subject(type=subjecttype_region, name="Germany-North")
        DBSession.add(subject_germany_north)
        subject_germany_west = Subject(type=subjecttype_region, name="Germany-West")
        DBSession.add(subject_germany_west)
        subject_germany_east = Subject(type=subjecttype_region, name="Germany-East")
        DBSession.add(subject_germany_east)
        subject_germany_south = Subject(type=subjecttype_region, name="Germany-South")
        DBSession.add(subject_germany_south)

        subject_paderborn = Subject(type=subjecttype_city, name="Paderborn")
        DBSession.add(subject_paderborn)
        subject_bielefeld = Subject(type=subjecttype_city, name="Bielefeld")
        DBSession.add(subject_bielefeld)
        subject_detmold = Subject(type=subjecttype_city, name="Detmold")
        DBSession.add(subject_detmold)
        subject_berlin = Subject(type=subjecttype_city, name="Berlin")
        DBSession.add(subject_berlin)

        subject_sales = Subject(type=subjecttype_team, name="Sales")
        DBSession.add(subject_sales)

        subject_tech = Subject(type=subjecttype_team, name="Tech")
        DBSession.add(subject_tech)

        subject_junior_developer = Subject(type=subjecttype_position, name="Junior Developer")
        DBSession.add(subject_junior_developer)

        subject_senior_developer = Subject(type=subjecttype_position, name="Senior Developer")
        DBSession.add(subject_senior_developer)

        subject_manager = Subject(type=subjecttype_position, name="Manager")
        DBSession.add(subject_manager)

        subject_promoter = Subject(type=subjecttype_position, name="Promoter")
        DBSession.add(subject_promoter)
        DBSession.flush()

        lang_de = Language(name="de")
        lang_en = Language(name="en")
        DBSession.add(lang_de)
        DBSession.add(lang_en)

        var_invited_users = Variable(name="invite_users")
        DBSession.add(var_invited_users)

        var_invited_users = Variable(name="participate",
                                     group="none")
        DBSession.add(var_invited_users)

        achievementcategory_community = AchievementCategory(name="community")
        DBSession.add(achievementcategory_community)

        achievement_invite = Achievement(name='invite_users',
                                         evaluation="immediately",
                                         maxtimes=20,
                                         achievementcategory=achievementcategory_community,
                                         condition='{"term": {"type": "literal", "variable": "invite_users"}}',
                                         goal="5*level",
                                         operator="geq",
                                         player_subjecttype=subjecttype_user
                                         )
        DBSession.add(achievement_invite)


        achievementcategory_sports = AchievementCategory(name="sports")
        DBSession.add(achievementcategory_sports)

        achievement_fittest = Achievement(name='fittest',
                                          relevance="friends",
                                          maxlevel=100,
                                          achievementcategory=achievementcategory_sports,
                                          condition='{"term": {"key": ["5","7","9"], "type": "literal", "key_operator": "IN", "variable": "participate"}}',
                                          evaluation="weekly",
                                          goal="5*level",
                                          player_subjecttype=subjecttype_user
                                          )
        DBSession.add(achievement_fittest)

        property_name = AchievementProperty(name='name')
        DBSession.add(property_name)

        property_xp = AchievementProperty(name='xp')
        DBSession.add(property_xp)

        property_icon = AchievementProperty(name='icon')
        DBSession.add(property_icon)

        reward_badge = Reward(name='badge', rewarded_subjecttype=subjecttype_user)
        DBSession.add(reward_badge)

        reward_image = Reward(name='backgroud_image', rewarded_subjecttype=subjecttype_user)
        DBSession.add(reward_image)

        transvar_invite_name = add_translation_variable(name="invite_users_achievement_name")
        add_translation(transvar_invite_name, lang_en, 'Invite ${5*level} Users')
        add_translation(transvar_invite_name, lang_de, 'Lade ${5*level} Freunde ein')


        DBSession.add(AchievementAchievementProperty(achievement=achievement_invite, property=property_name, value_translation=transvar_invite_name))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_invite, property=property_xp, value='${100 * level}'))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_invite, property=property_icon, value="https://www.gamification-software.com/img/running.png"))

        DBSession.add(AchievementReward(achievement=achievement_invite, reward=reward_badge, value="https://www.gamification-software.com/img/trophy.png", from_level=5))
        DBSession.add(AchievementReward(achievement=achievement_invite, reward=reward_image, value="https://www.gamification-software.com/img/video-controller-336657_1920.jpg", from_level=5))

        transvar_fittest_name = add_translation_variable(name="fittest_achievement_name")
        add_translation(transvar_fittest_name, lang_en, 'Do the most sport activities among your friends')
        add_translation(transvar_fittest_name, lang_de, 'Mache unter deinen Freunden am meisten Sportaktivitäten')

        DBSession.add(AchievementAchievementProperty(achievement=achievement_fittest, property=property_name, value_translation=transvar_fittest_name))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_fittest, property=property_xp, value='${50 + (200 * level)}'))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_fittest, property=property_icon, value="https://www.gamification-software.com/img/colorwheel.png"))

        DBSession.add(AchievementReward(achievement=achievement_fittest, reward=reward_badge, value="https://www.gamification-software.com/img/easel.png", from_level=1))
        DBSession.add(AchievementReward(achievement=achievement_fittest, reward=reward_image, value="https://www.gamification-software.com/img/game-characters-622654.jpg", from_level=1))

        DBSession.flush()

        user1 = Subject(lat=10, lng=50, timezone="Europe/Berlin", name="Fritz", type=subjecttype_user)
        user2 = Subject(lat=10, lng=50, timezone="US/Eastern", name="Ludwig", type=subjecttype_user)
        user3 = Subject(lat=10, lng=50, name="Helene", type=subjecttype_user)

        user1.friends.append(user2)
        user1.friends.append(user3)

        user2.friends.append(user1)
        user2.friends.append(user3)

        user3.friends.append(user1)
        user3.friends.append(user2)

        user1.part_of_subjects.append(subject_bielefeld)
        user1.part_of_subjects.append(subject_sales)
        user1.part_of_subjects.append(subject_manager)

        user2.part_of_subjects.append(subject_bielefeld)
        user2.part_of_subjects.append(subject_sales)
        user2.part_of_subjects.append(subject_promoter)

        user3.part_of_subjects.append(subject_paderborn)
        user3.part_of_subjects.append(subject_sales)
        user3.part_of_subjects.append(subject_promoter)

        DBSession.add(user2)
        DBSession.add(user3)
        DBSession.flush()

        try:
            auth_user = DBSession.query(AuthUser).filter_by(email="admin@gamification-software.com").first()

            if not auth_user:
                auth_user = AuthUser(subject=user1, email="admin@gamification-software.com", password="test123", active=True)
                DBSession.add(auth_user)

            auth_role = DBSession.query(AuthRole).filter_by(name="Global Admin").first()

            if not auth_role:
                auth_role = AuthRole(name="Global Admin")
                DBSession.add(auth_role)

            DBSession.flush()

            for perm in yield_all_perms():
                if not exists_by_expr(t_auth_roles_permissions, and_(
                    t_auth_roles_permissions.c.auth_role_id == auth_role.id,
                    t_auth_roles_permissions.c.name == perm[0]
                )):
                    DBSession.add(AuthRolePermission(role=auth_role, name=perm[0]))

            auth_user.roles.append(auth_role)
            DBSession.add(auth_user)
        except ImportError as e:
            print("[auth] feature not installed - not importing auth demo data")


if __name__ == '__main__':
    main()