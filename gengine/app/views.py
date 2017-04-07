# -*- coding: utf-8 -*-
import traceback

import binascii
from http.cookies import SimpleCookie

import base64
import copy
import datetime

import json

import pytz
from pyramid.request import Request
from pyramid.response import Response
from pyramid.settings import asbool
from sqlalchemy.sql.expression import select, and_

from gengine.app.permissions import perm_own_update_user_infos, perm_global_update_user_infos, perm_global_delete_user, perm_own_delete_user, \
    perm_global_access_admin_ui, perm_global_register_device, perm_own_register_device, perm_global_read_messages, \
    perm_own_read_messages
from gengine.base.model import valid_timezone, exists_by_expr, update_connection
from gengine.base.errors import APIError
from pyramid.exceptions import NotFound
from pyramid.renderers import render
from pyramid.view import view_config
from pyramid.wsgi import wsgiapp2
from werkzeug import DebuggedApplication

from gengine.app.admin import adminapp
from gengine.app.formular import FormularEvaluationException
from gengine.app.model import (
    User,
    Achievement,
    Value,
    Variable,
    AuthUser, AuthToken, t_users, t_auth_users, t_auth_users_roles, t_auth_roles, t_auth_roles_permissions, UserDevice,
    t_user_device, t_user_messages, UserMessage)
from gengine.base.settings import get_settings
from gengine.metadata import DBSession
from gengine.wsgiutil import HTTPSProxied

@view_config(route_name='add_or_update_user', renderer='string', request_method="POST")
def add_or_update_user(request):
    """add a user and set its metadata"""

    user_id = int(request.matchdict["user_id"])

    if asbool(get_settings().get("enable_user_authentication", False)):
        #ensure that the user exists and we have the permission to update it
        may_update = request.has_perm(perm_global_update_user_infos) or request.has_perm(perm_own_update_user_infos) and request.user.id == user_id
        if not may_update:
            raise APIError(403, "forbidden", "You may not edit this user.")

        #if not exists_by_expr(t_users,t_users.c.id==user_id):
        #    raise APIError(403, "forbidden", "The user does not exist. As the user authentication is enabled, you need to create the AuthUser first.")


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
    
    country=None
    if len(request.POST.get("country",""))>0:
        country = request.POST["country"]
    
    region=None
    if len(request.POST.get("region",""))>0:
        region = request.POST["region"]
    
    city=None
    if len(request.POST.get("city",""))>0:
        city = request.POST["city"]

    language = None
    if len(request.POST.get("language", "")) > 0:
        language= request.POST["language"]

    additional_public_data = {}
    if len(request.POST.get("additional_public_data", "")) > 0:
        try:
            additional_public_data = json.loads(request.POST["additional_public_data"])
        except:
            additional_public_data = {}


    User.set_infos(user_id=user_id,
                   lat=lat,
                   lng=lon,
                   timezone=timezone,
                   country=country,
                   region=region,
                   city=city,
                   language=language,
                   friends=friends,
                   groups=groups,
                   additional_public_data = additional_public_data)
    return {"status": "OK", "user" : User.full_output(user_id)}

@view_config(route_name='delete_user', renderer='string', request_method="DELETE")
def delete_user(request):
    """delete a user completely"""
    user_id = int(request.matchdict["user_id"])

    if asbool(get_settings().get("enable_user_authentication", False)):
        # ensure that the user exists and we have the permission to update it
        may_delete = request.has_perm(perm_global_delete_user) or request.has_perm(perm_own_delete_user) and request.user.id == user_id
        if not may_delete:
            raise APIError(403, "forbidden", "You may not delete this user.")

    User.delete_user(user_id)
    return {"status": "OK"}

def _get_progress(achievements_for_user, requesting_user):

    achievements = Achievement.get_achievements_by_user_for_today(achievements_for_user)

    def ea(achievement, achievement_date, execute_triggers):
        try:
            return Achievement.evaluate(achievements_for_user, achievement["id"], achievement_date, execute_triggers=execute_triggers)
        except FormularEvaluationException as e:
            return { "error": "Cannot evaluate formular: " + e.message, "id" : achievement["id"] }
        except Exception as e:
            tb = traceback.format_exc()
            return { "error": tb, "id" : achievement["id"] }

    check = lambda x : x!=None and not "error" in x and (x["hidden"]==False or x["level"]>0)

    def may_view(achievement, requesting_user):
        if not asbool(get_settings().get("enable_user_authentication", False)):
            return True

        if achievement["view_permission"] == "everyone":
            return True
        if achievement["view_permission"] == "own" and achievements_for_user["id"] == requesting_user["id"]:
            return True
        return False

    evaluatelist = []
    now = datetime.datetime.now(pytz.timezone(achievements_for_user["timezone"]))
    for achievement in achievements:
        if may_view(achievement, requesting_user):
            achievement_dates = set()
            d = max(achievement["created_at"], achievements_for_user["created_at"]).replace(tzinfo=pytz.utc)
            dr = Achievement.get_datetime_for_evaluation_type(
                achievement["evaluation_timezone"],
                achievement["evaluation"],
                dt=d
            )

            achievement_dates.add(dr)
            if dr != None:
                while d <= now:
                    if achievement["evaluation"] == "yearly":
                        d += datetime.timedelta(days=364)
                    elif achievement["evaluation"] == "monthly":
                        d += datetime.timedelta(days=28)
                    elif achievement["evaluation"] == "weekly":
                        d += datetime.timedelta(days=6)
                    elif achievement["evaluation"] == "daily":
                        d += datetime.timedelta(hours=23)
                    else:
                        break # should not happen

                    dr = Achievement.get_datetime_for_evaluation_type(
                        achievement["evaluation_timezone"],
                        achievement["evaluation"],
                        dt=d
                    )

                    if dr <= now:
                        achievement_dates.add(dr)

            i=0
            for achievement_date in reversed(sorted(achievement_dates)):
                # We execute the goal triggers only for the newest and previous period, not for any periods longer ago
                # (To not send messages for very old things....)
                evaluatelist.append(ea(achievement, achievement_date, execute_triggers=(i == 0 or i == 1 or achievement_date == None)))
                i += 1


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
    """get all relevant data concerning the user's progress"""
    try:
        user_id = int(request.matchdict["user_id"])
    except:
        raise APIError(400, "illegal_user_id", "no valid user_id given")
    
    user = User.get_user(user_id)
    if not user:
        raise APIError(404, "user_not_found", "user not found")

    output = _get_progress(achievements_for_user=user, requesting_user=request.user)
    output = copy.deepcopy(output)

    for i in range(len(output["achievements"])):
        if "new_levels" in output["achievements"][i]:
            del output["achievements"][i]["new_levels"]

    return output

@view_config(route_name='increase_value', renderer='json', request_method="POST")
@view_config(route_name='increase_value_with_key', renderer='json', request_method="POST")
def increase_value(request):
    """increase a value for the user"""
    
    user_id = int(request.matchdict["user_id"])
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
    
    user = User.get_user(user_id)
    if not user:
        raise APIError(404, "user_not_found", "user not found")
    
    variable = Variable.get_variable_by_name(variable_name)
    if not variable:
        raise APIError(404, "variable_not_found", "variable not found")

    if asbool(get_settings().get("enable_user_authentication", False)):
        if not Variable.may_increase(variable, request, user_id):
            raise APIError(403, "forbidden", "You may not increase the variable for this user.")
    
    Value.increase_value(variable_name, user, value, key) 
    
    output = _get_progress(achievements_for_user=user, requesting_user=request.user)
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
    ret = {}
    for user_id, values in doc.items():
        user = User.get_user(user_id)
        if not user:
            raise APIError(404, "user_not_found", "user %s not found" % (user_id,))

        for variable_name, values_and_keys in values.items():
            for value_and_key in values_and_keys:
                variable = Variable.get_variable_by_name(variable_name)

                if asbool(get_settings().get("enable_user_authentication", False)):
                    if not Variable.may_increase(variable, request, user_id):
                        raise APIError(403, "forbidden", "You may not increase the variable %s for user %s." % (variable_name, user_id))
                
                if not variable:
                    raise APIError(404, "variable_not_found", "variable %s not found" % (variable_name,))

                if not 'value' in value_and_key:
                    raise APIError(400, "variable_not_found", "illegal value for %s" % (variable_name,))
                
                value = value_and_key['value']
                key = value_and_key.get('key','')
                
                Value.increase_value(variable_name, user, value, key)

        output = _get_progress(achievements_for_user=user, requesting_user=request.user)
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
            ret[user_id]=output
    
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

    level_output = Achievement.basic_output(achievement, [], True, level).get("levels").get(str(level), {"properties": {}, "rewards": {}})
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

        token = AuthToken.generate_token()
        tokenObj = AuthToken(
            user_id = user.id,
            token = token
        )

        DBSession.add(tokenObj)

    return {
        "token" : token,
        "user" : User.full_output(user.user_id),
    }

@view_config(route_name='register_device', renderer='json', request_method="POST")
def register_device(request):
    try:
        doc = request.json_body
    except:
        raise APIError(400, "invalid_json", "no valid json body")

    user_id = int(request.matchdict["user_id"])

    device_id = doc.get("device_id")
    push_id = doc.get("push_id")
    device_os = doc.get("device_os")
    app_version = doc.get("app_version")

    if not device_id \
            or not push_id \
            or not user_id \
            or not device_os \
            or not app_version:
        raise APIError(400, "register_device.required_fields",
                       "Required fields: device_id, push_id, device_os, app_version")

    if asbool(get_settings().get("enable_user_authentication", False)):
        may_register = request.has_perm(perm_global_register_device) or request.has_perm(
            perm_own_register_device) and str(request.user.id) == str(user_id)
        if not may_register:
            raise APIError(403, "forbidden", "You may not register devices for this user.")

    if not exists_by_expr(t_users, t_users.c.id==user_id):
        raise APIError(404, "register_device.user_not_found",
                       "There is no user with this id.")

    UserDevice.add_or_update_device(user_id = user_id, device_id = device_id, push_id = push_id, device_os = device_os, app_version = app_version)

    return {
        "status" : "ok"
    }

@view_config(route_name='get_messages', renderer='json', request_method="GET")
def get_messages(request):
    try:
        user_id = int(request.matchdict["user_id"])
    except:
        user_id = None

    try:
        offset = int(request.GET.get("offset",0))
    except:
        offset = 0

    limit = 100

    if asbool(get_settings().get("enable_user_authentication", False)):
        may_read_messages = request.has_perm(perm_global_read_messages) or request.has_perm(
            perm_own_read_messages) and str(request.user.id) == str(user_id)
        if not may_read_messages:
            raise APIError(403, "forbidden", "You may not read the messages of this user.")

    if not exists_by_expr(t_users, t_users.c.id == user_id):
        raise APIError(404, "get_messages.user_not_found",
                       "There is no user with this id.")

    q = t_user_messages.select().where(t_user_messages.c.user_id==user_id).order_by(t_user_messages.c.created_at.desc()).limit(limit).offset(offset)
    rows = DBSession.execute(q).fetchall()

    return {
        "messages" : [{
            "id" : message["id"],
            "text" : UserMessage.get_text(message),
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

    user_id = int(request.matchdict["user_id"])

    if asbool(get_settings().get("enable_user_authentication", False)):
        may_read_messages = request.has_perm(perm_global_read_messages) or request.has_perm(
            perm_own_read_messages) and str(request.user.id) == str(user_id)
        if not may_read_messages:
            raise APIError(403, "forbidden", "You may not read the messages of this user.")

    if not exists_by_expr(t_users, t_users.c.id == user_id):
        raise APIError(404, "set_messages_read.user_not_found", "There is no user with this id.")

    message_id = doc.get("message_id")
    q = select([t_user_messages.c.id,
        t_user_messages.c.created_at], from_obj=t_user_messages).where(and_(t_user_messages.c.id==message_id,
                                                                       t_user_messages.c.user_id==user_id))
    msg = DBSession.execute(q).fetchone()
    if not msg:
        raise APIError(404, "set_messages_read.message_not_found", "There is no message with this id.")

    uS = update_connection()
    uS.execute(t_user_messages.update().values({
        "is_read" : True
    }).where(and_(
        t_user_messages.c.user_id == user_id,
        t_user_messages.c.created_at <= msg["created_at"]
    )))

    return {
        "status" : "ok"
    }

@view_config(route_name='admin_app')
@wsgiapp2
def admin_tenant(environ, start_response):

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
        j = t_auth_users.join(t_auth_users_roles).join(t_auth_roles).join(t_auth_roles_permissions)
        q = select([t_auth_roles_permissions.c.name], from_obj=j).where(t_auth_users.c.user_id==user.user_id)
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