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
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
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
    
    engine = engine_from_config(settings, 'sqlalchemy.')
    
    config = Configurator(settings=settings)
    pyramid_dogpile_cache.includeme(config)
    
    from ..models import (
        DBSession,
        Base,
        Achievement,
        Goal,
        Variable,
        User,
        Language,
        TranslationVariable,
        Translation
    )
    
    DBSession.configure(bind=engine)
    
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    def add_translation_variable(name):
        t = TranslationVariable(name=name)
        DBSession.add(t)
        return t
    
    def add_translation(variable,lang,text):
        tr = Translation(translationvariable=variable,text=text,language=lang)
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