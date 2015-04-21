# -*- coding: utf-8 -*-
import datetime, os

from pyramid.config import Configurator
from pyramid.renderers import JSON

from sqlalchemy import engine_from_config

from sqlalchemy.orm import sessionmaker
from pyramid.settings import asbool
from gengine.wsgiutil import HTTPSProxied, init_reverse_proxy


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_dogpile_cache')
    
    durl = os.environ.get("DATABASE_URL") #heroku
    if durl:
        settings['sqlalchemy.url']=durl
        
    murl = os.environ.get("MEMCACHED_URL") #heroku
    if murl:
        settings['urlcache_url']=murl
    
    engine = engine_from_config(settings, 'sqlalchemy.',connect_args={"options": "-c timezone=utc"},)
    
    config.include("pyramid_tm")
    
    from gengine.metadata import init_session, init_declarative_base, init_db
    init_session()
    init_declarative_base()
    init_db(engine)
    
    config.include('pyramid_chameleon')
    
    urlprefix = settings.get("urlprefix","")
    urlcacheid = settings.get("urlcacheid","gengine")
    force_https = asbool(settings.get("force_https",False))
    init_reverse_proxy(force_https,urlprefix)
    
    urlcache_url = settings.get("urlcache_url","127.0.0.1:11211")
    urlcache_active = asbool(os.environ.get("URLCACHE_ACTIVE", settings.get("urlcache_active",True)))
	
    #routes
    config.add_route('get_progress', urlprefix+'/progress/{user_id}')
    config.add_route('increase_value', urlprefix+'/increase_value/{variable_name}/{user_id}')
    config.add_route('increase_value_with_key', urlprefix+'/increase_value/{variable_name}/{user_id}/{key}')
    config.add_route('add_or_update_user', urlprefix+'/add_or_update_user/{user_id}')
    config.add_route('delete_user', urlprefix+'/delete_user/{user_id}')
    config.add_route('get_achievement_level', urlprefix+'/achievement/{achievement_id}/level/{level}')
    #config.add_route('get_achievement_reward', urlprefix+'/achievement_reward/{achievement_reward_id}')
    
    config.add_route('admin', '/*subpath') #prefix is set in flaskadmin.py
    
    from gengine.flaskadmin import init_flaskadmin
    init_flaskadmin(urlprefix=urlprefix,
                    secret=settings.get("flaskadmin_secret","fKY7kJ2xSrbPC5yieEjV"))

    from urlcache import setup_urlcache
    setup_urlcache(prefix=urlprefix,
                   url = urlcache_url,
                   active = urlcache_active,
                   id = urlcacheid)

    #date serialization    
    json_renderer = JSON()
    def datetime_adapter(obj, request):
        return obj.isoformat()
    json_renderer.add_adapter(datetime.datetime, datetime_adapter)
    config.add_renderer('json', json_renderer)
    
    config.scan()
    
    return HTTPSProxied(config.make_wsgi_app())