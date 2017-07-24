# -*- coding: utf-8 -*-
import jinja2
import os
import pkg_resources
from flask import Flask
from flask_admin import Admin
from flask.globals import request
from flask.helpers import send_from_directory, flash
from flask_admin.actions import action
from flask_admin.base import BaseView, expose
from flask_admin.contrib.sqla.filters import IntEqualFilter, BaseSQLAFilter
from flask_admin.contrib.sqla.view import ModelView
from flask_admin.model.form import InlineFormAdmin
from gengine.app.jsscripts import get_jsmain, get_cssmain
from gengine.base.util import dt_now
from pyramid.settings import asbool
from wtforms import BooleanField
from wtforms.form import Form

from gengine.app.model import DBSession, Variable, AchievementCategory, Achievement, AchievementProperty, AchievementAchievementProperty, AchievementReward,\
    Reward, Subject, Evaluation, Progress, Value, TranslationVariable, Language, Translation, \
    AuthUser, AuthRole, AuthRolePermission, AchievementTrigger, AchievementTriggerStep, SubjectMessage, Task, TaskExecution, SubjectType
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

    class TranslationInlineModelForm(InlineFormAdmin):
        form_columns = ('id', 'language', 'text')

    class ModelViewTranslationVariable(ModelView):
        column_list = ('name',)
        column_searchable_list = ('name',)
        inline_models = (TranslationInlineModelForm(Translation),)

        def __init__(self, session, **kwargs):
            super(ModelViewTranslationVariable, self).__init__(TranslationVariable, session, **kwargs)

    class ModelViewAchievementCategory(ModelView):
        column_list = ('name',)
        column_searchable_list = ('name',)
        form_excluded_columns = ('achievements',)
        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewAchievementCategory, self).__init__(AchievementCategory, session, **kwargs)

    class ModelViewAchievement(ModelView):
        column_list = ('name','evaluation','valid_start','valid_end','relevance', 'condition','operator','goal','timespan','priority','achievement')
        column_searchable_list = ('name',)
        form_excluded_columns = ('rewards','subjects','goals','properties','updated_at', 'properties','triggers')
        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewAchievement, self).__init__(Achievement, session, **kwargs)

    class ModelViewVariable(ModelView):
        form_excluded_columns =('values',)

        def __init__(self, session, **kwargs):
            super(ModelViewVariable, self).__init__(Variable, session, **kwargs)

    class AchievementTriggerStepInlineModelForm(InlineFormAdmin):
        form_columns = (
            'id',
            'step',
            'condition_type',
            'condition_percentage',
            'action_type',
            'action_translation',
            'action_subjecttype',
            'action_value',
            'action_variable'
        )

    class ModelViewAchievementTrigger(ModelView):
        form_columns = (
            'name',
            'achievement',
            'steps',
            'execute_when_complete',
        )
        inline_models = (AchievementTriggerStepInlineModelForm(AchievementTriggerStep),)

        def __init__(self, session, **kwargs):
            super(ModelViewAchievementTrigger, self).__init__(AchievementTrigger, session, **kwargs)

    class ModelViewValue(ModelView):
        # Disable model creation
        can_create = False
        can_edit = False
        can_delete = False

        # Override displayed fields
        column_list = ('subject','variable','datetime','key','value')

        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewValue, self).__init__(Value, session, **kwargs)

    class ModelViewProgress(ModelView):
        # Disable model creation
        can_create = False
        can_edit = False
        can_delete = False

        # Override displayed fields
        column_list = ('goal','subject','value','updated_at')

        column_filters = (IntEqualFilter(Subject.id, 'SubjectID'),
                          Achievement.id)

        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewProgress, self).__init__(Progress, session, **kwargs)

    class ModelViewAchievementProperty(ModelView):
        column_list = ('id','name')
        form_excluded_columns = ('achievements',)
        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewAchievementProperty, self).__init__(AchievementProperty, session, **kwargs)

    class ModelViewLanguage(ModelView):
        column_list = ('id','name')
        form_excluded_columns = ('subjects',)

        def __init__(self, session, **kwargs):
            super(ModelViewLanguage, self).__init__(Language, session, **kwargs)

    class ModelViewReward(ModelView):
        column_list = ('id','name')
        form_excluded_columns = ('achievements',)
        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewReward, self).__init__(Reward, session, **kwargs)

    class ModelViewSubject(ModelView):
        column_list = ('id','type','name','lat','lng','timezone','country','region','city','created_at')
        form_columns = ('name', 'type', 'timezone', 'language', 'lat', 'lng', 'additional_public_data')
        fast_mass_delete = True

        def __init__(self, session, **kwargs):
            super(ModelViewSubject, self).__init__(Subject, session, **kwargs)

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
        column_list = ('id', 'subject_id', 'email', 'active', 'created_at')
        form_columns = ('subject_id', 'email', 'password', 'active', 'roles')
        column_labels = {'password': 'Password'}

        def __init__(self, session, **kwargs):
            super(ModelViewAuthUser, self).__init__(AuthUser, session, **kwargs)

    class PermissionInlineModelForm(InlineFormAdmin):
        form_columns = ('id','name')
        form_choices = {
            "name" : sorted(list(yield_all_perms()), key=lambda x: x[1])
        }

    class ModelViewAuthRole(ModelView):
        column_list = ('id', 'name', 'permissions')
        form_excluded_columns = ('users',)
        inline_models = (PermissionInlineModelForm(AuthRolePermission),)

        def __init__(self, session, **kwargs):
            super(ModelViewAuthRole, self).__init__(AuthRole, session, **kwargs)


    class ModelViewSubjectMessage(ModelView):
        column_list = ('subject','text','created_at','is_read')
        column_details_list = ('subject', 'text', 'created_at', 'is_read', 'params')
        can_edit = False
        can_view_details = True

        def __init__(self, session, **kwargs):
            super(ModelViewSubjectMessage, self).__init__(SubjectMessage, session, **kwargs)

    from gengine.app.registries import get_task_registry
    enginetasks = get_task_registry().registrations

    class ModelViewTask(ModelView):
        can_view_details = True

        column_list = ('entry_name', 'task_name', 'config', 'cron')
        column_details_list = ('id','entry_name', 'task_name', 'config', 'cron', 'is_removed', 'is_auto_created', 'is_manually_modified')
        form_excluded_columns = ('is_removed', 'is_auto_created', 'is_manually_modified', 'executions')
        form_choices = {'task_name': [
            (x, x) for x in enginetasks.keys()
        ]}

        def __init__(self, session, **kwargs):
            super(ModelViewTask, self).__init__(Task, session, **kwargs)

        @action('execute', 'Execute now', 'Are you sure you want to execute the selected task?')
        def action_execute(self, ids):
            from gengine.metadata import DBSession
            from gengine.app.model import t_tasks, t_taskexecutions
            from gengine.app.registries import get_task_registry
            tasks = DBSession.execute(
                t_tasks.select().where(t_tasks.c.id.in_(*ids))
            ).fetchall()

            for task in tasks:
                result = get_task_registry().execute(
                    name=task["task_name"],
                    config=task["config"]
                )
                logged = result.get("log", None)
                success = result.get("success", True)

                DBSession.bind.execute(
                    t_taskexecutions.insert().values({
                        'task_id': task["id"],
                        'planned_at': dt_now(),
                        'finished_at': dt_now(),
                        'log': logged,
                        'success': success
                    })
                )

            flash("Executed")


    class ModelViewTaskExecution(ModelView):
        column_list = ('task.entry_name', 'task.task_name', 'planned_at', 'finished_at', 'success')
        column_details_list = ('id', 'task.entry_name', 'task.task_name', 'planned_at', 'finished_at', 'success', 'log')
        can_create = False
        can_edit = False
        can_view_details = True

        def __init__(self, session, **kwargs):
            super(ModelViewTaskExecution, self).__init__(TaskExecution, session, **kwargs)


    class ModelViewSubjectType(ModelView):
        column_list = ('id', 'name')
        form_columns = ('name', 'part_of_types')
        can_view_details = True

        def __init__(self, session, **kwargs):
            super(ModelViewSubjectType, self).__init__(SubjectType, session, **kwargs)


    if not override_flaskadminapp:
        adminapp = Flask(__name__)
        adminapp.debug=True
        adminapp.secret_key = secret
        adminapp.config.update(dict(
            PREFERRED_URL_SCHEME='https'
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
                 "urlprefix" : get_settings().get("urlprefix","/"),
                 "jsmain": get_jsmain(),
                 "cssmain": get_cssmain()
                 }
    
    if not override_admin:
        admin = Admin(adminapp,
                      name="Gamification Engine - Admin Control Panel",
                      base_template='admin_layout.html',
                      url=urlprefix+""
                      )
    else:
        admin = override_admin

            
    admin.add_view(ModelViewAchievement(DBSession, category="Rules"))
    admin.add_view(ModelViewAchievementTrigger(DBSession, category="Rules"))

    admin.add_view(ModelView(AchievementAchievementProperty, DBSession, category="Rules", name="Achievement Property Values"))
    admin.add_view(ModelView(AchievementReward, DBSession, category="Rules", name="Achievement Reward Values"))
    admin.add_view(ModelViewTranslationVariable(DBSession, category="Rules"))
    admin.add_view(ModelView(Translation,DBSession, category="Rules"))
    
    admin.add_view(ModelViewAchievementCategory(DBSession, category="Settings"))
    admin.add_view(ModelViewVariable(DBSession, category="Settings"))
    admin.add_view(ModelViewAchievementProperty(DBSession, category="Settings", name="Achievement Property Types"))
    admin.add_view(ModelViewReward(DBSession, category="Settings", name="Achievement Reward Types"))
    admin.add_view(ModelViewLanguage(DBSession, category="Settings"))
    admin.add_view(ModelViewTask(DBSession, category="Settings"))
    admin.add_view(ModelViewTaskExecution(DBSession, category="Settings"))
    admin.add_view(MaintenanceView(name="Maintenance", category="Settings", url="maintenance"))

    admin.add_view(ModelViewAuthUser(DBSession, category="Authentication"))
    admin.add_view(ModelViewAuthRole(DBSession, category="Authentication"))

    admin.add_view(ModelViewSubjectType(DBSession, category="Subjects"))

    admin.add_view(ModelViewValue(DBSession, category="Debug"))
    admin.add_view(ModelViewProgress(DBSession, category="Debug"))
    admin.add_view(ModelViewSubject(DBSession, category="Subjects"))
    admin.add_view(ModelView(Evaluation, DBSession, category="Debug"))
    admin.add_view(ModelViewSubjectMessage(DBSession, category="Debug"))

    from gengine.app.registries import get_admin_extension_registry
    get_admin_extension_registry().run_extensions(adminapp=adminapp, admin=admin)


    class GroupAssignmentView(BaseView):
        @expose('/', methods=('GET', 'POST'))
        def index(self):
            return self.render(template='jscomponent.html', component="GroupAssignment")

    admin.add_view(GroupAssignmentView(name='Assign Subjects', endpoint='group_assignment', category="Subjects"))

    class LeaderboardCreationView(BaseView):
        @expose('/', methods=('GET', 'POST'))
        def index(self):
            return self.render(template='jscomponent.html', component="LeaderboardCreation")

    admin.add_view(LeaderboardCreationView(name='Create Leaderboards', endpoint='leaderboard_creation', category="Rules"))
