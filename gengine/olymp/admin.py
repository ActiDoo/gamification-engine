# -*- coding: utf-8 -*-
import jinja2
import os
import pkg_resources
from flask import Flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.helpers import send_from_directory

from gengine.metadata import DBSession
from gengine.olymp.model import Tenant

olympadminapp = None
admin = None

def resole_uri(uri):
    from pyramid.path import PkgResourcesAssetDescriptor
    pkg_name, path = uri.split(":", 1)
    a = PkgResourcesAssetDescriptor(pkg_name, path)
    absolute = a.abspath()  # this is sometimes not absolute :-/
    absolute = os.path.abspath(absolute)  # so we make it absolute
    return absolute


def get_static_view(folder, olympadminapp):
    folder = resole_uri(folder)

    def send_static_file(filename):
        cache_timeout = olympadminapp.get_send_file_max_age(filename)
        return send_from_directory(folder, filename, cache_timeout=cache_timeout)

    return send_static_file


def init_admin(urlprefix="", secret="fKY7kJ2xSrbPC5yieEjV", override_admin=None, override_olympadminapp=None):
    global olympadminapp, admin

    if not override_olympadminapp:
        olympadminapp = Flask(__name__)
        olympadminapp.debug = True
        olympadminapp.secret_key = secret
        olympadminapp.config.update(dict(
            PREFERRED_URL_SCHEME='https'
        ))
    else:
        olympadminapp = override_olympadminapp

    # lets add our template directory
    my_loader = jinja2.ChoiceLoader([
        olympadminapp.jinja_loader,
        jinja2.FileSystemLoader(resole_uri("gengine:olymp/templates")),
    ])
    olympadminapp.jinja_loader = my_loader

    olympadminapp.add_url_rule('/static_gengine/<path:filename>',
                                endpoint='static_gengine',
                                view_func=get_static_view('gengine:olymp/static', olympadminapp))

    @olympadminapp.context_processor
    def inject_version():
        return {"gamification_engine_version": pkg_resources.get_distribution("gamification-engine").version}

    if not override_admin:
        admin = Admin(olympadminapp,
                      name = "Zeus at Olympia - Gamification Engine",
                      base_template = 'admin_layout.html',
                      url = urlprefix + "/admin"
                      )
    else:
        admin = override_admin

    admin.add_view(ModelViewTenant(DBSession))

class ModelViewTenant(ModelView):
    column_list = ('id',)
    column_searchable_list = ('id',)
    form_columns = ('id',)
    fast_mass_delete = True

    def __init__(self, session, **kwargs):
        super(ModelViewTenant, self).__init__(Tenant, session, **kwargs)

