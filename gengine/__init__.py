# -*- coding: utf-8 -*-
from pyramid.events import NewRequest

from gengine.base.context import reset_context

__version__ = '0.2.0'

import datetime

import os
from pyramid.config import Configurator
from pyramid.renderers import JSON
from pyramid.settings import asbool
from sqlalchemy import engine_from_config

from gengine.wsgiutil import HTTPSProxied, init_reverse_proxy


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.', connect_args={"options": "-c timezone=utc"}, )

    from gengine.metadata import init_session, init_declarative_base, init_db

    init_session()
    init_declarative_base()
    init_db(engine)

    from gengine.base.monkeypatch_flaskadmin import do_monkeypatch
    do_monkeypatch()

    config = Configurator(settings=settings)

    def reset_context_on_new_request(event):
        reset_context()
    config.add_subscriber(reset_context_on_new_request,NewRequest)
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
    from gengine.app.route import config_routes as config_tenant_routes

    config.include(config_tenant_routes, route_prefix=urlprefix)

    config.add_route('admin_tenant', '/*subpath') #prefix is set in flaskadmin.py

    from gengine.app.admin import init_admin as init_tenantadmin
    init_tenantadmin(urlprefix=urlprefix,
                     secret=settings.get("flaskadmin_secret","fKY7kJ2xSrbPC5yieEjV"))

    from gengine.base.cache import setup_urlcache
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