# -*- coding: utf-8 -*-
from pyramid import events

__version__ = '0.1.36'

import datetime, os

from pyramid.config import Configurator
from pyramid.renderers import JSON

from sqlalchemy import engine_from_config

from pyramid.settings import asbool
from gengine.wsgiutil import HTTPSProxied, init_reverse_proxy

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.', connect_args={"options": "-c timezone=utc"}, )

    from gengine.metadata import init_session, init_declarative_base, init_db

    init_session()
    init_declarative_base()
    init_db(engine)

    from gengine.resources import root_factory
    config = Configurator(settings=settings, root_factory=root_factory)
    config.include('pyramid_dogpile_cache')
    
    durl = os.environ.get("DATABASE_URL") #heroku
    if durl:
        settings['sqlalchemy.url']=durl
        
    murl = os.environ.get("MEMCACHED_URL") #heroku
    if murl:
        settings['urlcache_url']=murl
    

    config.include("pyramid_tm")
    config.include('pyramid_chameleon')
    
    urlprefix = settings.get("urlprefix","")
    urlcacheid = settings.get("urlcacheid","gengine")
    force_https = asbool(settings.get("force_https",False))
    init_reverse_proxy(force_https,urlprefix)
    
    urlcache_url = settings.get("urlcache_url","127.0.0.1:11211")
    urlcache_active = asbool(os.environ.get("URLCACHE_ACTIVE", settings.get("urlcache_active",True)))
	
    #routes
    config.add_route('get_progress', urlprefix+'/t/{tenant}/progress/{user_id}', traverse="/t/{tenant}")
    config.add_route('increase_value', urlprefix+'/t/{tenant}/increase_value/{variable_name}/{user_id}', traverse="/t/{tenant}")
    config.add_route('increase_value_with_key', urlprefix+'/t/{tenant}/increase_value/{variable_name}/{user_id}/{key}', traverse="/t/{tenant}")
    config.add_route('increase_multi_values', urlprefix+'/t/{tenant}/increase_multi_values', traverse="/t/{tenant}")
    config.add_route('add_or_update_user', urlprefix+'/t/{tenant}/add_or_update_user/{user_id}', traverse="/t/{tenant}")
    config.add_route('delete_user', urlprefix+'/t/{tenant}/delete_user/{user_id}', traverse="/t/{tenant}")
    config.add_route('get_achievement_level', urlprefix+'/t/{tenant}/achievement/{achievement_id}/level/{level}', traverse="/t/{tenant}")
    #config.add_route('get_achievement_reward', urlprefix+'/achievement_reward/{achievement_reward_id}')
    
    config.add_route('admin_tenant', '/t/{tenant}/*subpath', traverse="/t/{tenant}") #prefix is set in flaskadmin.py

    config.add_route('admin_olymp', '/olymp/*subpath')  # prefix is set in flaskadmin.py

    from gengine.tenantadmin import init_admin as init_tenantadmin
    init_tenantadmin(urlprefix=urlprefix,
               secret=settings.get("flaskadmin_secret","fKY7kJ2xSrbPC5yieEjV"))

    from gengine.olympadmin import init_admin as init_olympadmin
    init_olympadmin(urlprefix=urlprefix,
               secret=settings.get("flaskadmin_secret", "fKY7kJ2xSrbPC5yieEjV"))

    from .cache import setup_urlcache
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