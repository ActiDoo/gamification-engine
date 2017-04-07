# -*- coding: utf-8 -*-
import jinja2
import os
import pkg_resources
from flask import Flask
from flask_admin import Admin
from flask.globals import request
from flask.helpers import send_from_directory
from flask_admin.base import BaseView, expose
from flask_admin.contrib.sqla.filters import IntEqualFilter
from flask_admin.contrib.sqla.view import ModelView
from flask_admin.model.form import InlineFormAdmin
from pyramid.settings import asbool
from wtforms import BooleanField
from wtforms.form import Form

from gengine.app.model import DBSession, Variable, Goal, AchievementCategory, Achievement, AchievementProperty, GoalProperty, AchievementAchievementProperty, AchievementReward,\
                           GoalGoalProperty, Reward, User, GoalEvaluationCache, Value, AchievementUser, TranslationVariable, Language, Translation, \
    AuthUser, AuthRole, AuthRolePermission, GoalTrigger, GoalTriggerStep, UserMessage
from gengine.app.permissions import yield_all_perms
from gengine.base.settings import get_settings

adminapp=None
admin=None


def resolve_uri(uri):
    from pyramid.path import PkgResourcesAssetDescriptor
    pkg_name,path=uri.split(":",1)
    a = PkgResourcesAssetDescriptor(pkg_name,path)
    absolute = a.abspath() #this is sometimes not absolute :-/
    absolute = os.path.abspath(absolute) #so we make it absolute
    return absolute

resole_uri = resolve_uri # there was a typing error once...

def get_static_view(folder,flaskadminapp):
    folder=resole_uri(folder)
    
    def send_static_file(filename):
        cache_timeout = flaskadminapp.get_send_file_max_age(filename)
        return send_from_directory(folder, filename, cache_timeout=cache_timeout)
    
    return send_static_file
    
def init_admin(urlprefix="",secret="fKY7kJ2xSrbPC5yieEjV",override_admin=None,override_flaskadminapp=None):
    global adminapp, admin
    
    if not override_flaskadminapp:
        adminapp = Flask(__name__)
        adminapp.debug=True
        adminapp.secret_key = secret
        adminapp.config.update(dict(
            PREFERRED_URL_SCHEME = 'https'
        ))
    else:
        adminapp = override_flaskadminapp

    # lets add our template directory
    my_loader = jinja2.ChoiceLoader([
        adminapp.jinja_loader,
        jinja2.FileSystemLoader(resole_uri("gengine:app/templates")),
    ])

    adminapp.jinja_loader = my_loader
        
    adminapp.add_url_rule('/static_gengine/<path:filename>',
                          endpoint='static_gengine',
                          view_func=get_static_view('gengine:app/static', adminapp))
    
    @adminapp.context_processor
    def inject_version():
        return { "gamification_engine_version" : pkg_resources.get_distribution("gamification-engine").version,
                 "settings_enable_authentication" : asbool(get_settings().get("enable_user_authentication",False)),
                 "urlprefix" : get_settings().get("urlprefix","/")}
    
    if not override_admin:
        admin = Admin(adminapp,
                      name="Gamification Engine - Admin Control Panel",
                      base_template='admin_layout.html',
                      url=urlprefix+""
                      )
    else:
        admin = override_admin
            
    admin.add_view(ModelViewAchievement(DBSession, category="Rules"))
    admin.add_view(ModelViewGoal(DBSession, category="Rules"))
    admin.add_view(ModelViewGoalTrigger(DBSession, category="Rules"))

    admin.add_view(ModelView(AchievementAchievementProperty, DBSession, category="Rules", name="Achievement Property Values"))
    admin.add_view(ModelView(AchievementReward, DBSession, category="Rules", name="Achievement Reward Values"))
    admin.add_view(ModelView(GoalGoalProperty, DBSession, category="Rules", name="Goal Property Values"))
    admin.add_view(ModelViewTranslationVariable(DBSession, category="Rules"))
    admin.add_view(ModelView(Translation,DBSession, category="Rules"))
    
    admin.add_view(ModelViewAchievementCategory(DBSession, category="Settings"))
    admin.add_view(ModelViewVariable(DBSession, category="Settings"))
    admin.add_view(ModelViewAchievementProperty(DBSession, category="Settings", name="Achievement Property Types"))
    admin.add_view(ModelViewReward(DBSession, category="Settings", name="Achievement Reward Types"))
    admin.add_view(ModelViewGoalProperty(DBSession, category="Settings", name="Goal Property Types"))
    admin.add_view(ModelView(Language, DBSession, category="Settings"))
    admin.add_view(MaintenanceView(name="Maintenance", category="Settings", url="maintenance"))

    admin.add_view(ModelViewAuthUser(DBSession, category="Authentication"))
    admin.add_view(ModelViewAuthRole(DBSession, category="Authentication"))
    
    admin.add_view(ModelViewValue(DBSession, category="Debug"))
    admin.add_view(ModelViewGoalEvaluationCache(DBSession, category="Debug"))
    admin.add_view(ModelViewUser(DBSession, category="Debug"))
    admin.add_view(ModelView(AchievementUser, DBSession, category="Debug"))
    admin.add_view(ModelViewUserMessage(DBSession, category="Debug"))

class TranslationInlineModelForm(InlineFormAdmin):
    form_columns = ('id','language','text')

class ModelViewTranslationVariable(ModelView):
    column_list = ('name',)
    column_searchable_list = ('name',)
    inline_models = (TranslationInlineModelForm(Translation),)
    
    def __init__(self, session, **kwargs):
        super(ModelViewTranslationVariable, self).__init__(TranslationVariable, session, **kwargs)

class ModelViewAchievementCategory(ModelView):
    column_list = ('name',)
    column_searchable_list = ('name',)
    form_excluded_columns =('achievements',)
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewAchievementCategory, self).__init__(AchievementCategory, session, **kwargs)

class ModelViewAchievement(ModelView):
    column_list = ('name','evaluation','valid_start','valid_end','relevance')
    column_searchable_list = ('name',)
    form_excluded_columns =('rewards','users','goals','properties','updated_at')
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewAchievement, self).__init__(Achievement, session, **kwargs)

class ModelViewVariable(ModelView):
    form_excluded_columns =('values',)
    
    def __init__(self, session, **kwargs):
        super(ModelViewVariable, self).__init__(Variable, session, **kwargs)

class GoalTriggerStepInlineModelForm(InlineFormAdmin):
    form_columns = (
        'id',
        'step',
        'condition_type',
        'condition_percentage',
        'action_type',
        'action_translation',
    )

class ModelViewGoalTrigger(ModelView):
    form_columns = (
        'name',
        'goal',
        'steps',
        'execute_when_complete'
    )
    inline_models = (GoalTriggerStepInlineModelForm(GoalTriggerStep),)

    def __init__(self, session, **kwargs):
        super(ModelViewGoalTrigger, self).__init__(GoalTrigger, session, **kwargs)

class ModelViewGoal(ModelView):
    column_list = ('condition','operator','goal','timespan','priority','achievement','updated_at')
    form_excluded_columns =('properties','triggers')
    #column_searchable_list = ('name',)
    column_filters = (Achievement.id,)
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewGoal, self).__init__(Goal, session, **kwargs)

class ModelViewValue(ModelView):
    # Disable model creation
    can_create = False
    can_edit = False
    can_delete = False
    
    # Override displayed fields
    column_list = ('user','variable','datetime','key','value')
    
    fast_mass_delete = True

    def __init__(self, session, **kwargs):
        super(ModelViewValue, self).__init__(Value, session, **kwargs)
        
class ModelViewGoalEvaluationCache(ModelView):
    # Disable model creation
    can_create = False
    can_edit = False
    can_delete = False
    
    # Override displayed fields
    column_list = ('goal','user','achieved','value','updated_at')
    
    column_filters = (IntEqualFilter(User.id, 'UserID'),
                      Goal.id)
    
    fast_mass_delete = True

    def __init__(self, session, **kwargs):
        super(ModelViewGoalEvaluationCache, self).__init__(GoalEvaluationCache, session, **kwargs)

class ModelViewAchievementProperty(ModelView):
    column_list = ('id','name')
    form_excluded_columns = ('achievements',)
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewAchievementProperty, self).__init__(AchievementProperty, session, **kwargs)
        
class ModelViewGoalProperty(ModelView):
    column_list = ('id','name')
    form_excluded_columns = ('goals',)
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewGoalProperty, self).__init__(GoalProperty, session, **kwargs)
        
class ModelViewReward(ModelView):
    column_list = ('id','name')
    form_excluded_columns = ('achievements',)
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewReward, self).__init__(Reward, session, **kwargs)
        
class ModelViewUser(ModelView):
    column_list = ('id','lat','lng','timezone','country','region','city','created_at')
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewUser, self).__init__(User, session, **kwargs)

class ClearCacheForm(Form):
    clear_check = BooleanField(label="Delete all caches?")

class MaintenanceView(BaseView):
    @expose('/',methods=('GET','POST',))
    def index(self):
        self._template_args['msgs'] = []
        self._template_args['clear_caches_form'] = self.clear_caches_form = ClearCacheForm(request.form)
        
        if request.method == 'POST':
            from gengine.app.cache import clear_all_caches
            if self.clear_caches_form.clear_check.data:
                clear_all_caches()
                self._template_args['msgs'].append("All caches cleared!")    
        return self.render(template="admin_maintenance.html")

class ModelViewAuthUser(ModelView):
    column_list = ('user_id', 'email', 'active', 'created_at')
    form_columns = ('user_id','email', 'password', 'active', 'roles')
    column_labels = {'password': 'Password'}

    def __init__(self, session, **kwargs):
        super(ModelViewAuthUser, self).__init__(AuthUser, session, **kwargs)

class PermissionInlineModelForm(InlineFormAdmin):
    form_columns = ('id','name')
    form_choices = {
        "name" : sorted(list(yield_all_perms()),key=lambda x:x[1])
    }

class ModelViewAuthRole(ModelView):
    column_list = ('id', 'name', 'permissions')
    form_excluded_columns = ('users')
    inline_models = (PermissionInlineModelForm(AuthRolePermission),)

    def __init__(self, session, **kwargs):
        super(ModelViewAuthRole, self).__init__(AuthRole, session, **kwargs)


class ModelViewUserMessage(ModelView):
    column_list = ('user','text','created_at','is_read')
    column_details_list = ('user', 'text', 'created_at', 'is_read', 'params')
    can_edit = False
    can_view_details = True

    def __init__(self, session, **kwargs):
        super(ModelViewUserMessage, self).__init__(UserMessage, session, **kwargs)
