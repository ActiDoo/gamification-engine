# -*- coding: utf-8 -*-
from flask import Flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView

from gengine.models import DBSession, Variable, Goal, AchievementCategory, Achievement, AchievementProperty, GoalProperty, AchievementAchievementProperty, AchievementReward,\
                           GoalGoalProperty, Reward, User, GoalEvaluationCache, Value, AchievementUser, TranslationVariable, Language, Translation
from flask_admin.contrib.sqla.filters import BooleanEqualFilter, IntEqualFilter
from flask_admin.base import AdminIndexView, BaseView, expose
from wtforms import BooleanField
from flask.globals import request
from wtforms.form import Form
import pkg_resources, os
from flask.helpers import send_from_directory
import jinja2
from flask_admin.model.form import InlineFormAdmin

flaskadminapp=None
admin=None


def resole_uri(uri):
    from pyramid.path import PkgResourcesAssetDescriptor
    pkg_name,path=uri.split(":",1)
    a = PkgResourcesAssetDescriptor(pkg_name,path)
    absolute = a.abspath() #this is sometimes not absolute :-/
    absolute = os.path.abspath(absolute) #so we make it absolute
    return absolute

def get_static_view(folder,flaskadminapp):
    folder=resole_uri(folder)
    
    def send_static_file(filename):
        cache_timeout = flaskadminapp.get_send_file_max_age(filename)
        return send_from_directory(folder, filename, cache_timeout=cache_timeout)
    
    return send_static_file
    
def init_flaskadmin(urlprefix="",secret="fKY7kJ2xSrbPC5yieEjV",override_admin=None,override_flaskadminapp=None):
    global flaskadminapp, admin
    
    if not override_flaskadminapp:
        flaskadminapp = Flask(__name__)
        flaskadminapp.debug=True
        flaskadminapp.secret_key = secret
        flaskadminapp.config.update(dict(
            PREFERRED_URL_SCHEME = 'https'
        ))
    else:
        flaskadminapp = override_flaskadminapp

        # lets add our template directory
        my_loader = jinja2.ChoiceLoader([
            flaskadminapp.jinja_loader,
            jinja2.FileSystemLoader(resole_uri("gengine:templates")),
        ])
        flaskadminapp.jinja_loader = my_loader
        
    flaskadminapp.add_url_rule('/static_gengine/<path:filename>',
                               endpoint='static_gengine',
                               view_func=get_static_view('gengine:flask_static',flaskadminapp))
    
    @flaskadminapp.context_processor
    def inject_version():
        return { "gamification_engine_version" : pkg_resources.get_distribution("gamification-engine").version }
    
    if not override_admin:
        admin = Admin(flaskadminapp,
                      name="Gamification Engine - Admin Control Panel",
                      base_template='admin_layout.html',
                      url=urlprefix+"/admin"
                     )
    else:
        admin = override_admin
            
    admin.add_view(ModelViewAchievement(DBSession, category="Rules"))
    admin.add_view(ModelViewGoal(DBSession, category="Rules"))
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
    
    admin.add_view(ModelViewValue(DBSession, category="Debug"))
    admin.add_view(ModelViewGoalEvaluationCache(DBSession, category="Debug"))
    admin.add_view(ModelViewUser(DBSession, category="Debug"))
    admin.add_view(ModelView(AchievementUser, DBSession, category="Debug"))

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
    column_list = ('name','valid_start','valid_end','relevance')
    column_searchable_list = ('name',)
    form_excluded_columns =('rewards','users','goals','properties','updated_at')
    fast_mass_delete = True
    
    def __init__(self, session, **kwargs):
        super(ModelViewAchievement, self).__init__(Achievement, session, **kwargs)

class ModelViewVariable(ModelView):
    form_excluded_columns =('values',)
    
    def __init__(self, session, **kwargs):
        super(ModelViewVariable, self).__init__(Variable, session, **kwargs)

class ModelViewGoal(ModelView):
    column_list = ('condition','evaluation','operator','goal','timespan','priority','achievement','updated_at')
    form_excluded_columns =('properties',)
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
            from models import clear_all_caches
            if self.clear_caches_form.clear_check.data:
                clear_all_caches()
                self._template_args['msgs'].append("All caches cleared!")    
        return self.render(template="admin_maintenance.html")
    