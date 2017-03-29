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
from sqlalchemy.sql.schema import Table

from gengine.app.cache import init_caches
from gengine.app.permissions import perm_global_delete_user, perm_global_increase_value, perm_global_update_user_infos, \
    perm_global_access_admin_ui, perm_global_read_messages, perm_global_register_device
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

    alembic_cfg = Config(attributes={
        'engine' : engine,
        'schema' : 'public'
    })
    script_location = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'app/alembic'
    )
    alembic_cfg.set_main_option("script_location", script_location)

    do_upgrade = options.get("upgrade",False)
    if not do_upgrade:
        #init
        from gengine.app import model

        tables = [t for name, t in model.__dict__.items() if isinstance(t, Table)]
        Base.metadata.create_all(engine, tables=tables)

        command.stamp(alembic_cfg, "head")

        if options.get("populate_demo", False):
            populate_demo(DBSession)
    else:
        #upgrade
        command.upgrade(alembic_cfg,'head')

    admin_user = options.get("admin_user", False)
    admin_password = options.get("admin_password", False)

    if admin_user and admin_password:
        create_user(DBSession = DBSession, user=admin_user,password=admin_password)

    engine.dispose()

def create_user(DBSession, user, password):
    from gengine.app.model import (
        AuthUser,
        User,
        AuthRole,
        AuthRolePermission
    )
    with transaction.manager:
        existing = DBSession.query(AuthUser).filter_by(email=user).first()
        if not existing:
            try:
                user1 = User(id=1, lat=10, lng=50, timezone="Europe/Berlin")
                DBSession.add(user1)
                DBSession.flush()

                auth_user = AuthUser(user_id=user1.id, email=user, password=password, active=True)
                DBSession.add(auth_user)

                auth_role = AuthRole(name="Global Admin")
                DBSession.add(auth_role)

                DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_access_admin_ui))
                DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_delete_user))
                DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_increase_value))
                DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_update_user_infos))
                DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_read_messages))
                DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_register_device))

                auth_user.roles.append(auth_role)
                DBSession.add(auth_user)
            except:
                pass

def populate_demo(DBSession):

    from gengine.app.model import (
        Achievement,
        AchievementCategory,
        Goal,
        Variable,
        User,
        Language,
        TranslationVariable,
        Translation,
        GoalProperty,
        GoalGoalProperty,
        Reward,
        AchievementProperty,
        AchievementAchievementProperty,
        AchievementReward,
        AuthUser,
        AuthRole,
        AuthRolePermission
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
        lang_de = Language(name="de")
        lang_en = Language(name="en")
        DBSession.add(lang_de)
        DBSession.add(lang_en)

        var_invited_users = Variable(name="invite_users")
        DBSession.add(var_invited_users)

        var_invited_users = Variable(name="participate",
                                     group="none")
        DBSession.add(var_invited_users)

        goal_property_name = GoalProperty(name='name')
        DBSession.add(goal_property_name)

        achievementcategory_community = AchievementCategory(name="community")
        DBSession.add(achievementcategory_community)

        achievement_invite = Achievement(name='invite_users',
                                         evaluation="immediately",
                                         maxtimes=20,
                                         achievementcategory=achievementcategory_community)
        DBSession.add(achievement_invite)

        transvar_invite = add_translation_variable(name="invite_users_goal_name")
        add_translation(transvar_invite, lang_en, 'Invite ${5*level} Users')
        add_translation(transvar_invite, lang_de, 'Lade ${5*level} Freunde ein')

        achievement_invite_goal1 = Goal(name_translation=transvar_invite,
                                        condition='{"term": {"type": "literal", "variable": "invite_users"}}',
                                        goal="5*level",
                                        operator="geq",
                                        achievement=achievement_invite)
        DBSession.add(achievement_invite_goal1)

        DBSession.add(GoalGoalProperty(goal=achievement_invite_goal1, property=goal_property_name, value_translation=transvar_invite))

        achievementcategory_sports = AchievementCategory(name="sports")
        DBSession.add(achievementcategory_sports)

        achievement_fittest = Achievement(name='fittest',
                                          relevance="friends",
                                          maxlevel=100,
                                          achievementcategory=achievementcategory_sports)
        DBSession.add(achievement_fittest)

        transvar_fittest = add_translation_variable(name="fittest_goal_name")
        add_translation(transvar_fittest, lang_en, 'Do the most sport activities among your friends')
        add_translation(transvar_fittest, lang_de, 'Mache unter deinen Freunden am meisten Sportaktivitäten')

        achievement_fittest_goal1 = Goal(name_translation=transvar_fittest,
                                         condition='{"term": {"key": ["5","7","9"], "type": "literal", "key_operator": "IN", "variable": "participate"}}',
                                         evaluation="weekly",
                                         goal="5*level",
                                         achievement=achievement_fittest
                                         )

        DBSession.add(achievement_fittest_goal1)
        DBSession.add(GoalGoalProperty(goal=achievement_fittest_goal1, property=goal_property_name, value_translation=transvar_fittest))

        property_name = AchievementProperty(name='name')
        DBSession.add(property_name)

        property_xp = AchievementProperty(name='xp')
        DBSession.add(property_xp)

        property_icon = AchievementProperty(name='icon')
        DBSession.add(property_icon)

        reward_badge = Reward(name='badge')
        DBSession.add(reward_badge)

        reward_image = Reward(name='backgroud_image')
        DBSession.add(reward_image)

        transvar_invite_name = add_translation_variable(name="invite_achievement_name")
        add_translation(transvar_invite_name, lang_en, 'The Community!')
        add_translation(transvar_invite_name, lang_de, 'Die Community!')

        DBSession.add(AchievementAchievementProperty(achievement=achievement_invite, property=property_name, value_translation=transvar_invite_name))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_invite, property=property_xp, value='${100 * level}'))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_invite, property=property_icon, value="https://www.gamification-software.com/img/running.png"))

        DBSession.add(AchievementReward(achievement=achievement_invite, reward=reward_badge, value="https://www.gamification-software.com/img/trophy.png", from_level=5))
        DBSession.add(AchievementReward(achievement=achievement_invite, reward=reward_image, value="https://www.gamification-software.com/img/video-controller-336657_1920.jpg", from_level=5))

        transvar_fittest_name = add_translation_variable(name="fittest_achievement_name")
        add_translation(transvar_fittest_name, lang_en, 'The Fittest!')
        add_translation(transvar_fittest_name, lang_de, 'Der Fitteste!')

        DBSession.add(AchievementAchievementProperty(achievement=achievement_fittest, property=property_name, value_translation=transvar_fittest_name))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_fittest, property=property_xp, value='${50 + (200 * level)}'))
        DBSession.add(AchievementAchievementProperty(achievement=achievement_fittest, property=property_icon, value="https://www.gamification-software.com/img/colorwheel.png"))

        DBSession.add(AchievementReward(achievement=achievement_fittest, reward=reward_badge, value="https://www.gamification-software.com/img/easel.png", from_level=1))
        DBSession.add(AchievementReward(achievement=achievement_fittest, reward=reward_image, value="https://www.gamification-software.com/img/game-characters-622654.jpg", from_level=1))


        user1 = User(id=1,lat=10,lng=50,timezone="Europe/Berlin")
        user2 = User(id=2,lat=10,lng=50,timezone="US/Eastern")
        user3 = User(id=3,lat=10,lng=50)

        user1.friends.append(user2)
        user1.friends.append(user3)

        user2.friends.append(user1)
        user2.friends.append(user3)

        user3.friends.append(user1)
        user3.friends.append(user2)

        DBSession.add(user1)
        DBSession.add(user2)
        DBSession.add(user3)
        DBSession.flush()

        try:
            auth_user = AuthUser(user_id=user1.id,email="admin@gamification-software.com",password="test123",active=True)
            DBSession.add(auth_user)

            auth_role = AuthRole(name="Global Admin")
            DBSession.add(auth_role)

            DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_access_admin_ui))
            DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_delete_user))
            DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_increase_value))
            DBSession.add(AuthRolePermission(role=auth_role, name=perm_global_update_user_infos))

            auth_user.roles.append(auth_role)
            DBSession.add(auth_user)
        except ImportError as e:
            print("[auth] feature not installed - not importing auth demo data")


if __name__ == '__main__':
    main()