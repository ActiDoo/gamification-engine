# -*- coding: utf-8 -*-
import traceback

import binascii
from http.cookies import SimpleCookie

import base64
import copy
import datetime

import json

import pytz
from dateutil import relativedelta
from pyramid.request import Request
from pyramid.response import Response
from pyramid.settings import asbool
from sqlalchemy.sql.expression import select, and_

from gengine.app.permissions import perm_own_update_subject_infos, perm_global_manage_subjects, perm_global_delete_subject, perm_own_delete_subject, \
    perm_global_access_admin_ui, perm_global_register_device, perm_own_register_device, perm_global_read_messages, \
    perm_own_read_messages
from gengine.base.model import valid_timezone, exists_by_expr, update_connection
from gengine.base.errors import APIError
from pyramid.exceptions import NotFound
from pyramid.renderers import render
from pyramid.view import view_config
from pyramid.wsgi import wsgiapp2
from werkzeug import DebuggedApplication

from gengine.app.formular import FormularEvaluationException
from gengine.app.model import (
    Subject,
    Achievement,
    Value,
    Variable,
    AuthUser, AuthToken, t_subjects, t_auth_users, t_auth_users_roles, t_auth_roles, t_auth_roles_permissions,
    SubjectDevice,
    t_subject_device, t_subject_messages, SubjectMessage, AchievementDate)
from gengine.base.settings import get_settings
from gengine.base.util import dt_now
from gengine.metadata import DBSession
from gengine.wsgiutil import HTTPSProxied

@view_config(route_name='add_or_update_subject', renderer='string', request_method="POST")
def add_or_update_subject(request):
    """add a subject and set its metadata"""

    subject_id = int(request.matchdict["subject_id"])

    if asbool(get_settings().get("enable_user_authentication", False)):
        #ensure that the subject exists and we have the permission to update it
        may_update = request.has_perm(perm_global_manage_subjects) or request.has_perm(perm_own_update_subject_infos) and request.subject.id == subject_id
        if not may_update:
            raise APIError(403, "forbidden", "You may not edit this subject.")

        #if not exists_by_expr(t_subjects,t_subjects.c.id==subject_id):
        #    raise APIError(403, "forbidden", "The subject does not exist. As the user authentication is enabled, you need to create the AuthUser first.")


    lat=None
    if len(request.POST.get("lat",""))>0:
        lat = float(request.POST["lat"])
    
    lon=None
    if len(request.POST.get("lon",""))>0:
        lon = float(request.POST["lon"])
    
    friends=[]
    if len(request.POST.get("friends",""))>0:
        friends = [int(x) for x in request.POST["friends"].split(",")]
    
    groups=[]
    if len(request.POST.get("groups",""))>0:
        groups = [int(x) for x in request.POST["groups"].split(",")]
    
    timezone="UTC"
    if len(request.POST.get("timezone",""))>0:
        timezone = request.POST["timezone"]
    
    if not valid_timezone(timezone):
        timezone = 'UTC'

    language = None
    if len(request.POST.get("language", "")) > 0:
        language= request.POST["language"]

    additional_public_data = {}
    if len(request.POST.get("additional_public_data", "")) > 0:
        try:
            additional_public_data = json.loads(request.POST["additional_public_data"])
        except:
            additional_public_data = {}


    Subject.set_infos(subject_id=subject_id,
                   lat=lat,
                   lng=lon,
                   timezone=timezone,
                   language_id=language,
                   additional_public_data = additional_public_data)

    Subject.set_relations(subject_id=subject_id, relation_ids=friends)
    Subject.set_parent_subjects(subject_id=subject_id, parent_subject_ids=groups)

    return {"status": "OK", "subject" : Subject.full_output(subject_id)}

@view_config(route_name='delete_subject', renderer='string', request_method="DELETE")
def delete_subject(request):
    """delete a subject completely"""
    subject_id = int(request.matchdict["subject_id"])

    if asbool(get_settings().get("enable_user_authentication", False)):
        # ensure that the subject exists and we have the permission to update it
        may_delete = request.has_perm(perm_global_delete_subject) or request.has_perm(perm_own_delete_subject) and request.subject.id == subject_id
        if not may_delete:
            raise APIError(403, "forbidden", "You may not delete this subject.")

    Subject.delete_subject(subject_id)
    return {"status": "OK"}

def _get_progress(achievements_for_subject, requesting_subject, achievement_id=None, achievement_history=None):

    achievements = Achievement.get_achievements_by_subject_for_today(achievements_for_subject)
    if achievement_id:
        achievements = [x for x in achievements if int(x["id"]) == int(achievement_id)]

    def ea(achievement, achievement_date, context_subject_id, execute_triggers):
        try:
            return Achievement.evaluate(achievements_for_subject, achievement["id"], achievement_date, execute_triggers=execute_triggers, context_subject_id=context_subject_id)
        except FormularEvaluationException as e:
            return { "error": "Cannot evaluate formular: " + e.message, "id" : achievement["id"] }
        #except Exception as e:
        #    tb = traceback.format_exc()
        #    return { "error": tb, "id" : achievement["id"] }

    check = lambda x : x!=None and not "error" in x and (x["hidden"]==False or x["level"]>0)

    def may_view(achievement, requesting_subject):
        if not asbool(get_settings().get("enable_user_authentication", False)):
            return True

        if achievement["view_permission"] == "everyone":
            return True
        if achievement["view_permission"] == "own" and achievements_for_subject["id"] == requesting_subject["id"]:
            return True
        return False

    evaluatelist = []
    now = datetime.datetime.now(pytz.timezone(achievements_for_subject["timezone"]))
    for achievement in achievements:
        if may_view(achievement, requesting_subject):
            achievement_dates = set()
            d = max(achievement["created_at"], achievements_for_subject["created_at"]).replace(tzinfo=pytz.utc)
            dr = AchievementDate.compute(
                evaluation_timezone=achievement["evaluation_timezone"],
                evaluation_type=achievement["evaluation"],
                context_datetime=d,
                evaluation_shift=achievement["evaluation_shift"],
            )

            achievement_dates.add(dr)
            if dr != None:
                while d <= now:
                    if achievement["evaluation"] == "yearly":
                        d += relativedelta.relativedelta(years=1)
                    elif achievement["evaluation"] == "monthly":
                        d += relativedelta.relativedelta(months=1)
                    elif achievement["evaluation"] == "weekly":
                        d += relativedelta.relativedelta(weeks=1)
                    elif achievement["evaluation"] == "daily":
                        d += relativedelta.relativedelta(days=1)
                    else:
                        break # should not happen

                    dr = AchievementDate.compute(
                        evaluation_timezone=achievement["evaluation_timezone"],
                        evaluation_type=achievement["evaluation"],
                        context_datetime=d,
                        evaluation_shift=achievement["evaluation_shift"],
                    )

                    if dr.from_date <= now:
                        achievement_dates.add(dr)

            i=0
            for achievement_date in reversed(sorted(achievement_dates)):
                # We execute the goal triggers only for the newest and previous period, not for any periods longer ago
                # (To not send messages for very old things....)

                relevant_context_ids = Achievement.get_relevant_contexts(
                    subject_id=achievements_for_subject["id"],
                    achievement=achievement,
                    from_date=achievement_date.from_date if achievement_date else None,
                    to_date=achievement_date.to_date if achievement_date else None,
                    whole_time_required=False
                )

                for context_subject_id in relevant_context_ids:
                    evaluatelist.append(ea(achievement, achievement_date, context_subject_id, execute_triggers=(i == 0 or i == 1 or achievement_date == None)))
                    i += 1

                if achievement_history is not None and i >= achievement_history:
                    # achievement_history restricts the number of lookback items
                    break
    ret = {
        "achievements" : [
            x for x in evaluatelist if check(x)
        ],
        "achievement_errors" : [
            x for x in evaluatelist if x!=None and "error" in x
        ]
    }

    return ret


@view_config(route_name='get_progress', renderer='json', request_method="GET")
def get_progress(request):
    """get all relevant data concerning the subject's progress"""
    try:
        subject_id = int(request.matchdict["subject_id"])
    except:
        raise APIError(400, "illegal_subject_id", "no valid subject_id given")
    
    subject = Subject.get_subject(subject_id)
    if not subject:
        raise APIError(404, "subject_not_found", "subject not found")

    try:
        achievement_id = int(request.GET["achievement_id"])
    except:
        achievement_id = None

    try:
        achievement_history = int(request.GET["achievement_history"])
    except:
        achievement_history = 2

    output = _get_progress(achievements_for_subject=subject, requesting_subject=request.subject, achievement_id=achievement_id, achievement_history=achievement_history)
    output = copy.deepcopy(output)

    for i in range(len(output["achievements"])):
        if "new_levels" in output["achievements"][i]:
            del output["achievements"][i]["new_levels"]

    return output

@view_config(route_name='increase_value', renderer='json', request_method="POST")
@view_config(route_name='increase_value_with_key', renderer='json', request_method="POST")
def increase_value(request):
    """increase a value for the subject"""
    
    subject_id = int(request.matchdict["subject_id"])
    try:
        value = float(request.POST["value"])
    except:
        try:
            doc = request.json_body
            value = doc["value"]
        except:
            raise APIError(400,"invalid_value","Invalid value provided")
    
    key = request.matchdict["key"] if ("key" in request.matchdict and request.matchdict["key"] is not None) else ""
    variable_name = request.matchdict["variable_name"]
    
    subject = Subject.get_subject(subject_id)
    if not subject:
        raise APIError(404, "subject_not_found", "subject not found")
    
    variable = Variable.get_variable_by_name(variable_name)
    if not variable:
        raise APIError(404, "variable_not_found", "variable not found")

    if asbool(get_settings().get("enable_user_authentication", False)):
        if not AuthUser.may_increase(variable, request, subject_id):
            raise APIError(403, "forbidden", "You may not increase the variable for this subject.")
    
    Value.increase_value(variable_name, subject["id"], value, key, at_datetime=dt_now())

    try:
        achievement_history = int(request.GET["achievement_history"])
    except:
        achievement_history = 2
    
    output = _get_progress(achievements_for_subject=subject, requesting_subject=request.subject, achievement_history=achievement_history)
    output = copy.deepcopy(output)
    to_delete = list()
    for i in range(len(output["achievements"])):
        if len(output["achievements"][i]["new_levels"])>0:
            if "levels" in output["achievements"][i]:
                del output["achievements"][i]["levels"]
            if "priority" in output["achievements"][i]:
                del output["achievements"][i]["priority"]
            if "goals" in output["achievements"][i]:
                del output["achievements"][i]["goals"]
        else:
            to_delete.append(i)

    for i in sorted(to_delete,reverse=True):
        del output["achievements"][i]

    return output

@view_config(route_name="increase_multi_values", renderer="json", request_method="POST")
def increase_multi_values(request):
    try:
        doc = request.json_body
    except:
        raise APIError(400, "invalid_json", "no valid json body")

    try:
        achievement_history = int(request.GET["achievement_history"])
    except:
        achievement_history = 2

    ret = {}
    for subject_id, values in doc.items():
        subject = Subject.get_subject(subject_id)
        if not subject:
            raise APIError(404, "subject_not_found", "subject %s not found" % (subject_id,))

        for variable_name, values_and_keys in values.items():
            for value_and_key in values_and_keys:
                variable = Variable.get_variable_by_name(variable_name)

                if asbool(get_settings().get("enable_user_authentication", False)):
                    if not Variable.may_increase(variable, request, subject_id):
                        raise APIError(403, "forbidden", "You may not increase the variable %s for subject %s." % (variable_name, subject_id))
                
                if not variable:
                    raise APIError(404, "variable_not_found", "variable %s not found" % (variable_name,))

                if not 'value' in value_and_key:
                    raise APIError(400, "variable_not_found", "illegal value for %s" % (variable_name,))
                
                value = value_and_key['value']
                key = value_and_key.get('key','')
                
                Value.increase_value(variable_name, subject, value, key)

        output = _get_progress(achievements_for_subject=subject, requesting_subject=request.subject, achievement_history=achievement_history)
        output = copy.deepcopy(output)
        to_delete = list()
        for i in range(len(output["achievements"])):
            if len(output["achievements"][i]["new_levels"])>0:
                if "levels" in output["achievements"][i]:
                    del output["achievements"][i]["levels"]
                if "priority" in output["achievements"][i]:
                    del output["achievements"][i]["priority"]
                if "goals" in output["achievements"][i]:
                    del output["achievements"][i]["goals"]
            else:
                to_delete.append(i)

        for i in sorted(to_delete, reverse=True):
            del output["achievements"][i]

        if len(output["achievements"])>0 :
            ret[subject_id]=output
    
    return ret

@view_config(route_name='get_achievement_level', renderer='json', request_method="GET")
def get_achievement_level(request):
    """get all information about an achievement for a specific level""" 
    try:
        achievement_id = int(request.matchdict.get("achievement_id",None))
        level = int(request.matchdict.get("level",None))
    except:
        raise APIError(400, "invalid_input", "invalid input")

    achievement = Achievement.get_achievement(achievement_id)

    if not achievement:
        raise APIError(404, "achievement_not_found", "achievement not found")

    level_output = Achievement.basic_output(achievement, True, level).get("levels").get(str(level), {"properties": {}, "rewards": {}})
    if "goals" in level_output:
        del level_output["goals"]
    if "level" in level_output:
        del level_output["level"]

    return level_output


@view_config(route_name='auth_login', renderer='json', request_method="POST")
def auth_login(request):
    try:
        doc = request.json_body
    except:
        raise APIError(400, "invalid_json", "no valid json body")

    user = request.user
    email = doc.get("email")
    password = doc.get("password")

    if user:
        #already logged in
        token = user.get_or_create_token().token
    else:
        if not email or not password:
            raise APIError(400, "login.email_and_password_required", "You need to send your email and password.")

        user = DBSession.query(AuthUser).filter_by(email=email).first()

        if not user or not user.verify_password(password):
            raise APIError(401, "login.email_or_password_invalid", "Either the email address or the password is wrong.")

        if not user.active:
            raise APIError(400, "user_is_not_activated", "Your user is not activated.")

        if user.force_password_change:
            raise APIError(400, "user_has_to_change_password", "You have to change your password.")

        token = AuthToken.generate_token()
        tokenObj = AuthToken(
            auth_user_id = user.id,
            token = token
        )

        DBSession.add(tokenObj)

    return {
        "token" : token,
        "subject" : Subject.full_output(user.subject_id),
    }


@view_config(route_name='change_password', renderer='json', request_method="POST")
def change_password(request):
    try:
        doc = request.json_body
    except:
        raise APIError(400, "invalid_json", "no valid json body")

    email = doc.get("email")
    old_password = doc.get("old_password")
    new_password = doc.get("new_password")

    if not email or not old_password or not new_password:
        raise APIError(400, "change_password.email_and_old_password_and_new_password_required", "You need to send your email, the old password and a new password.")

    user = DBSession.query(AuthUser).filter_by(email=email).first()

    if not user or not user.verify_password(old_password):
        raise APIError(401, "change_password.email_or_old_password_invalid", "Either the email address or the old password is wrong.")

    if not user.active:
        raise APIError(400, "user_is_not_activated", "Your user is not activated.")

    if new_password == old_password:
        raise APIError(400, "change_password.may_not_be_the_same", "The new password may not be the same as the old one.")

    if not AuthUser.check_password_strength(new_password):
        raise APIError(400, "change_password.invalid_new_password", "The new password is too weak. Minimum length is 8 characters.")

    user.password = new_password
    user.force_password_change = False
    DBSession.add(user)

    token = AuthToken.generate_token()
    tokenObj = AuthToken(
        auth_user_id=user.id,
        token=token
    )
    DBSession.add(tokenObj)

    DBSession.flush()

    return {
        "token": token,
        "subject": Subject.full_output(user.subject_id),
    }


@view_config(route_name='register_device', renderer='json', request_method="POST")
def register_device(request):
    try:
        doc = request.json_body
    except:
        raise APIError(400, "invalid_json", "no valid json body")

    subject_id = int(request.matchdict["subject_id"])

    device_id = doc.get("device_id")
    push_id = doc.get("push_id")
    device_os = doc.get("device_os")
    app_version = doc.get("app_version")

    if not device_id \
            or not push_id \
            or not subject_id \
            or not device_os \
            or not app_version:
        raise APIError(400, "register_device.required_fields",
                       "Required fields: device_id, push_id, device_os, app_version")

    if asbool(get_settings().get("enable_user_authentication", False)):
        may_register = request.has_perm(perm_global_register_device) or request.has_perm(
            perm_own_register_device) and str(request.subject.id) == str(subject_id)
        if not may_register:
            raise APIError(403, "forbidden", "You may not register devices for this subject.")

    if not exists_by_expr(t_subjects, t_subjects.c.id==subject_id):
        raise APIError(404, "register_device.subject_not_found",
                       "There is no subject with this id.")

    SubjectDevice.add_or_update_device(subject_id = subject_id, device_id = device_id, push_id = push_id, device_os = device_os, app_version = app_version)

    return {
        "status" : "ok"
    }

@view_config(route_name='get_messages', renderer='json', request_method="GET")
def get_messages(request):
    try:
        subject_id = int(request.matchdict["subject_id"])
    except:
        subject_id = None

    try:
        offset = int(request.GET.get("offset",0))
    except:
        offset = 0

    limit = 100

    if asbool(get_settings().get("enable_user_authentication", False)):
        may_read_messages = request.has_perm(perm_global_read_messages) or request.has_perm(
            perm_own_read_messages) and str(request.subject.id) == str(subject_id)
        if not may_read_messages:
            raise APIError(403, "forbidden", "You may not read the messages of this subject.")

    if not exists_by_expr(t_subjects, t_subjects.c.id == subject_id):
        raise APIError(404, "get_messages.subject_not_found",
                       "There is no subject with this id.")

    q = t_subject_messages.select().where(t_subject_messages.c.subject_id==subject_id).order_by(t_subject_messages.c.created_at.desc()).limit(limit).offset(offset)
    rows = DBSession.execute(q).fetchall()

    return {
        "messages" : [{
            "id" : message["id"],
            "text" : SubjectMessage.get_text(message),
            "is_read" : message["is_read"],
            "created_at" : message["created_at"]
        } for message in rows]
    }


@view_config(route_name='read_messages', renderer='json', request_method="POST")
def set_messages_read(request):
    try:
        doc = request.json_body
    except:
        raise APIError(400, "invalid_json", "no valid json body")

    subject_id = int(request.matchdict["subject_id"])

    if asbool(get_settings().get("enable_user_authentication", False)):
        may_read_messages = request.has_perm(perm_global_read_messages) or request.has_perm(
            perm_own_read_messages) and str(request.subject.id) == str(subject_id)
        if not may_read_messages:
            raise APIError(403, "forbidden", "You may not read the messages of this subject.")

    if not exists_by_expr(t_subjects, t_subjects.c.id == subject_id):
        raise APIError(404, "set_messages_read.subject_not_found", "There is no subject with this id.")

    message_id = doc.get("message_id")
    q = select([t_subject_messages.c.id,
        t_subject_messages.c.created_at], from_obj=t_subject_messages).where(and_(t_subject_messages.c.id==message_id,
                                                                       t_subject_messages.c.subject_id==subject_id))
    msg = DBSession.execute(q).fetchone()
    if not msg:
        raise APIError(404, "set_messages_read.message_not_found", "There is no message with this id.")

    uS = update_connection()
    uS.execute(t_subject_messages.update().values({
        "is_read" : True
    }).where(and_(
        t_subject_messages.c.subject_id == subject_id,
        t_subject_messages.c.created_at <= msg["created_at"]
    )))

    return {
        "status" : "ok"
    }

@view_config(route_name='admin_app')
@wsgiapp2
def admin_tenant(environ, start_response):
    from gengine.app.admin import adminapp

    def admin_app(environ, start_response):
        #return HTTPSProxied(DebuggedApplication(adminapp.wsgi_app, True))(environ, start_response)
        return HTTPSProxied(adminapp.wsgi_app)(environ, start_response)

    def request_auth(environ, start_response):
        resp = Response()
        resp.status_code = 401
        resp.www_authenticate = 'Basic realm="%s"' % ("Gamification Engine Admin",)
        return resp(environ, start_response)

    if not asbool(get_settings().get("enable_user_authentication", False)):
        return admin_app(environ, start_response)

    req = Request(environ)

    def _get_basicauth_credentials(request):
        authorization = request.headers.get("authorization","")
        try:
            authmeth, auth = authorization.split(' ', 1)
        except ValueError:  # not enough values to unpack
            return None
        if authmeth.lower() == 'basic':
            try:
                auth = base64.b64decode(auth.strip()).decode("UTF-8")
            except binascii.Error:  # can't decode
                return None
            try:
                login, password = auth.split(':', 1)
            except ValueError:  # not enough values to unpack
                return None
            return {'login': login, 'password': password}
        return None

    user = None
    cred = _get_basicauth_credentials(req)
    token = req.cookies.get("token",None)
    if token:
        tokenObj = DBSession.query(AuthToken).filter(AuthToken.token == token).first()
        user = None
        if tokenObj and tokenObj.valid_until < datetime.datetime.utcnow():
            tokenObj.extend()
        if tokenObj:
            user = tokenObj.user

    if not user:
        if cred:
            user = DBSession.query(AuthUser).filter_by(email=cred["login"]).first()
        if not user or not user.verify_password(cred["password"]):
            return request_auth(environ, start_response)

    if user:
        j = t_auth_users_roles.join(t_auth_roles).join(t_auth_roles_permissions)
        q = select([t_auth_roles_permissions.c.name], from_obj=j).where(t_auth_users_roles.c.auth_user_id==user.id)
        permissions = [r["name"] for r in DBSession.execute(q).fetchall()]
        if not perm_global_access_admin_ui in permissions:
            return request_auth(environ, start_response)
        else:
            token_s = user.get_or_create_token().token

            def start_response_with_headers(status, headers, exc_info=None):

                cookie = SimpleCookie()
                cookie['X-Auth-Token'] = token_s
                cookie['X-Auth-Token']['path'] = get_settings().get("urlprefix", "").rstrip("/") + "/"

                headers.append(('Set-Cookie', cookie['X-Auth-Token'].OutputString()),)

                return start_response(status, headers, exc_info)

            return admin_app(environ, start_response_with_headers)