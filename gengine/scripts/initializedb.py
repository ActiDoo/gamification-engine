# -*- coding: utf-8 -*-
import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars
import pyramid_dogpile_cache
from pyramid.config import Configurator

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <alembic_uri> [var=value]\n'
          '(example: "%s production.ini alembic.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 3:
        usage(argv)
    config_uri = argv[1]
    alembic_uri = argv[2]
    options = parse_vars(argv[3:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    
    durl = os.environ.get("DATABASE_URL") #heroku
    if durl:
        settings['sqlalchemy.url']=durl
        
    murl = os.environ.get("MEMCACHED_URL")
    if murl:
        settings['urlcache_url']=murl
    
    engine = engine_from_config(settings, 'sqlalchemy.')
    
    config = Configurator(settings=settings)
    pyramid_dogpile_cache.includeme(config)
    
    from ..metadata import (
        init_session,
        init_declarative_base
    )
    init_session()
    init_declarative_base()
    
    from ..metadata import (
        Base,
        DBSession
    )
    
    from ..models import (
        Achievement,
        Goal,
        Variable,
        User,
        Language,
        TranslationVariable,
        Translation,
        Property,
        Reward,
        AchievementProperty, 
        AchievementReward
    )
    
    DBSession.configure(bind=engine)
    
    if options.get("reset_db",False):
        Base.metadata.drop_all(engine)
        
    Base.metadata.create_all(engine)
    
    
    # then, load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config(alembic_uri)
    command.stamp(alembic_cfg, "head")
    
    
    
    def add_translation_variable(name):
        t = TranslationVariable(name=name)
        DBSession.add(t)
        return t
    
    def add_translation(variable,lang,text):
        tr = Translation(translationvariable=variable,text=text,language=lang)
        DBSession.add(tr)
        return tr
    
    if options.get("populate_demo",False):
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
            
            achievement_invite = Achievement(name='invite_users',
                                             evaluation="immediately",
                                             maxtimes=20)
            DBSession.add(achievement_invite)
            
            transvar_invite = add_translation_variable(name="invite_users_goal_name")
            add_translation(transvar_invite, lang_en, '"Invite "+`(5*p.level)`+" Users"')
            add_translation(transvar_invite, lang_de, '"Lade "+`(5*p.level)`+" Freunde ein"')
            
            achievement_invite_goal1 = Goal(name_translation=transvar_invite,
                                            condition='p.var=="invite_users"',
                                            goal="5*p.level",
                                            operator="geq",
                                            achievement=achievement_invite)
            DBSession.add(achievement_invite_goal1)
            
            
            achievement_fittest = Achievement(name='fittest',
                                              relevance="friends",
                                              maxlevel=100)
            DBSession.add(achievement_fittest)
            
            transvar_fittest = add_translation_variable(name="fittest_goal_name")
            add_translation(transvar_fittest, lang_en, '"Do the most sport activities among your friends"')
            add_translation(transvar_fittest, lang_de, '"Mache unter deinen Freunden am meisten Sportaktivitäten"')
            
            achievement_fittest_goal1 = Goal(name_translation=transvar_fittest,
                                             condition='and_(p.var=="participate", p.key.in_(["5","7","9"]))',
                                             evaluation="weekly",
                                             goal="5*p.level",
                                             achievement=achievement_fittest
                                             )
            DBSession.add(achievement_fittest_goal1)

            property_name = Property(name='name')
            DBSession.add(property_name)
            
            property_xp = Property(name='xp')
            DBSession.add(property_xp)
            
            property_icon = Property(name='icon')
            DBSession.add(property_icon)
            
            property_description = Property(name='description')
            DBSession.add(property_description)

            reward_badge = Reward(name='badge')
            DBSession.add(reward_badge)
            
            reward_image = Reward(name='backgroud_image')
            DBSession.add(reward_image)

            transvar_invite_name = add_translation_variable(name="invite_achievement_name")
            add_translation(transvar_invite_name, lang_en, '"The Community!"')
            add_translation(transvar_invite_name, lang_de, '"Die Community!"')
            
            DBSession.add(AchievementProperty(achievement=achievement_invite, property=property_name, value_translation=transvar_invite_name))
            DBSession.add(AchievementProperty(achievement=achievement_invite, property=property_xp, value='100 * p.level'))
            DBSession.add(AchievementProperty(achievement=achievement_invite, property=property_icon, value="'https://www.gamification-software.com/img/running.png'"))
            DBSession.add(AchievementProperty(achievement=achievement_invite, property=property_description, value_translation=transvar_invite))
            
            DBSession.add(AchievementReward(achievement=achievement_invite, reward=reward_badge, value="'https://www.gamification-software.com/img/trophy.png'", from_level=5))
            DBSession.add(AchievementReward(achievement=achievement_invite, reward=reward_image, value="'https://www.gamification-software.com/img/video-controller-336657_1920.jpg'", from_level=5))
            
            transvar_fittest_name = add_translation_variable(name="fittest_achievement_name")
            add_translation(transvar_fittest_name, lang_en, '"The Fittest!"')
            add_translation(transvar_fittest_name, lang_de, '"Der Fitteste!"')
            
            DBSession.add(AchievementProperty(achievement=achievement_fittest, property=property_name, value_translation=transvar_fittest_name))
            DBSession.add(AchievementProperty(achievement=achievement_fittest, property=property_xp, value='50 + (200 * p.level)'))
            DBSession.add(AchievementProperty(achievement=achievement_fittest, property=property_icon, value="'https://www.gamification-software.com/img/colorwheel.png'"))
            DBSession.add(AchievementProperty(achievement=achievement_fittest, property=property_description, value_translation=transvar_fittest))
            
            DBSession.add(AchievementReward(achievement=achievement_fittest, reward=reward_badge, value="'https://www.gamification-software.com/img/easel.png'", from_level=1))
            DBSession.add(AchievementReward(achievement=achievement_fittest, reward=reward_image, value="'https://www.gamification-software.com/img/game-characters-622654.jpg'", from_level=1))
            
            
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