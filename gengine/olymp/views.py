# -*- coding: utf-8 -*-

from pyramid.view import view_config
from pyramid.wsgi import wsgiapp2
from werkzeug import DebuggedApplication

from gengine.olymp.admin import olympadminapp

from gengine.wsgiutil import HTTPSProxied

@view_config(route_name='admin_olymp')
@wsgiapp2
def admin_olymp(environ, start_response):
    return HTTPSProxied(DebuggedApplication(olympadminapp.wsgi_app, True))(environ, start_response)
