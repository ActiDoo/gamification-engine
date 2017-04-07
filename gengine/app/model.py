# -*- coding: utf-8 -*-
"""models including business logic"""

import datetime
import logging
from datetime import timedelta

import hashlib
import pytz
import sqlalchemy.types as ty
from sqlalchemy.dialects.postgresql import JSON
import sys

from pyramid.settings import asbool
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.schema import UniqueConstraint, Index

from gengine.app.permissions import perm_global_increase_value
from gengine.base.model import ABase, exists_by_expr, datetime_trunc, calc_distance, coords, update_connection
from gengine.app.cache import cache_general, cache_goal_evaluation, cache_achievement_eval, cache_achievements_users_levels, \
    cache_achievements_by_user_for_today, cache_translations
from sqlalchemy import (
    Table,
    ForeignKey,
    func,
    select,
    and_,
    or_,
    text,
    Column
, event)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import (
    mapper,
    relationship as sa_relationship,
    backref as sa_backref
)
from sqlalchemy.sql import bindparam

from gengine.base.settings import get_settings
from gengine.metadata import Base, DBSession

from gengine.app.formular import evaluate_condition, evaluate_value_expression, evaluate_string

log = logging.getLogger(__name__)

t_users = Table("users", Base.metadata,
    Column('id', ty.BigInteger, primary_key = True),
    Column("lat", ty.Float(Precision=64), nullable=True),
    Column("lng", ty.Float(Precision=64), nullable=True),
    Column("language_id", ty.Integer, ForeignKey("languages.id"), nullable=True),
    Column("timezone", ty.String(), nullable=False, default="UTC"),
    Column("country", ty.String(), nullable=True, default=None),
    Column("region", ty.String(), nullable=True, default=None),
    Column("city", ty.String(), nullable=True, default=None),
    Column("additional_public_data", JSON(), nullable=True, default=None),
    Column('created_at', ty.DateTime, nullable = False, default=datetime.datetime.utcnow),
)

t_auth_users = Table("auth_users", Base.metadata,
    Column('user_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column("email", ty.String, unique=True),
    Column("password_hash", ty.String, nullable=False),
    Column("password_salt", ty.Unicode, nullable=False),
    Column("active", ty.Boolean, nullable=False),
    Column('created_at', ty.DateTime, nullable = False, default=datetime.datetime.utcnow),
)

def get_default_token_valid_time():
    return datetime.datetime.utcnow() + datetime.timedelta(days=30)

t_auth_tokens = Table("auth_tokens", Base.metadata,
    Column("id", ty.BigInteger, primary_key=True),
    Column("user_id", ty.BigInteger, ForeignKey("auth_users.user_id", ondelete="CASCADE"), nullable=False),
    Column("token", ty.String, nullable=False),
    Column('valid_until', ty.DateTime, nullable = False, default=get_default_token_valid_time),
)

t_auth_roles = Table("auth_roles", Base.metadata,
    Column("id", ty.Integer, primary_key=True),
    Column("name", ty.String(100), unique=True),
)

t_auth_users_roles = Table("auth_users_roles", Base.metadata,
    Column("user_id", ty.BigInteger, ForeignKey("auth_users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("role_id", ty.BigInteger, ForeignKey("auth_roles.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

t_auth_roles_permissions = Table("auth_roles_permissions", Base.metadata,
    Column("id", ty.Integer, primary_key=True),
    Column("role_id", ty.Integer, ForeignKey("auth_roles.id", use_alter=True, ondelete="CASCADE"), nullable=False, index=True),
    Column("name", ty.String(255), nullable=False),
    UniqueConstraint("role_id", "name")
)

t_users_users = Table("users_users", Base.metadata,
    Column('from_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('to_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True, nullable=False)
)

t_groups = Table("groups", Base.metadata,
    Column('id', ty.BigInteger, primary_key = True),
)

t_users_groups = Table("users_groups", Base.metadata,
    Column('user_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('group_id', ty.BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), primary_key = True, nullable=False)
)

t_achievementcategories = Table('achievementcategories', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False),
)

t_achievements = Table('achievements', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column("achievementcategory_id", ty.Integer, ForeignKey("achievementcategories.id", ondelete="SET NULL"), index=True, nullable=True),
    Column('name', ty.String(255), nullable = False), #internal use
    Column('maxlevel',ty.Integer, nullable=False, default=1),
    Column('hidden',ty.Boolean, nullable=False, default=False),
    Column('valid_start',ty.Date, nullable=True),
    Column('valid_end',ty.Date, nullable=True),
    Column("lat", ty.Float(Precision=64), nullable=True),
    Column("lng", ty.Float(Precision=64), nullable=True),
    Column("max_distance", ty.Integer, nullable=True),
    Column('priority', ty.Integer, index=True, default=0),
    Column('evaluation', ty.Enum("immediately","daily","weekly","monthly","yearly","end", name="evaluation_types"), default="immediately", nullable=False),
    Column('evaluation_timezone', ty.String(), default=None, nullable=True),
    Column('relevance',ty.Enum("global","friends","city","own", name="relevance_types"), default="own"),
    Column('view_permission',ty.Enum("everyone", "own", name="achievement_view_permission"), default="everyone"),
    Column('created_at', ty.DateTime, nullable = False, default=datetime.datetime.utcnow),
)

t_goals = Table("goals", Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False, default=""), #internal use
    Column('name_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable = True),
    #TODO: deprecate name_translation
    Column('condition', ty.String(255), nullable=True),
    Column('timespan',ty.Integer, nullable=True),
    Column('group_by_key', ty.Boolean(), default=False),
    Column('group_by_dateformat', ty.String(255), nullable=True),
    Column('goal', ty.String(255), nullable=True),
    Column('operator', ty.Enum("geq","leq", name="goal_operators"), nullable=True),
    Column('maxmin', ty.Enum("max","min", name="goal_maxmin"), nullable=True, default="max"),
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False),
    Column('priority', ty.Integer, index=True, default=0),
)

t_goal_evaluation_cache = Table("goal_evaluation_cache", Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column("goal_id", ty.Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('achievement_date', ty.DateTime, nullable=True), # To identify the goals for monthly, weekly, ... achievements;
    Column("user_id", ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("achieved", ty.Boolean),
    Column("value", ty.Float),
)

Index("idx_goal_evaluation_cache_date_not_null_unique",
    t_goal_evaluation_cache.c.user_id,
    t_goal_evaluation_cache.c.goal_id,
    t_goal_evaluation_cache.c.achievement_date,
    unique=True,
    postgresql_where=t_goal_evaluation_cache.c.achievement_date!=None
)

Index("idx_goal_evaluation_cache_date_null_unique",
    t_goal_evaluation_cache.c.user_id,
    t_goal_evaluation_cache.c.goal_id,
    unique=True,
    postgresql_where=t_goal_evaluation_cache.c.achievement_date==None
)


t_variables = Table('variables', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False, index=True),
    Column('group', ty.Enum("year","month","week","day","none", name="variable_group_types"), nullable = False, default="none"),
    Column('increase_permission',ty.Enum("own", "admin", name="variable_increase_permission"), default="admin"),
)

t_values = Table('values', Base.metadata,
    Column('user_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('datetime', TIMESTAMP(timezone=True), primary_key = True, default=datetime.datetime.utcnow),
    Column('variable_id', ty.Integer, ForeignKey("variables.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('value', ty.Integer, nullable = False),
    Column('key', ty.String(100), primary_key=True, default=""),
)

t_achievementproperties = Table('achievementproperties', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False),
    Column('is_variable', ty.Boolean, nullable = False, default=False),
)

t_achievements_achievementproperties = Table('achievements_achievementproperties', Base.metadata,
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('property_id', ty.Integer, ForeignKey("achievementproperties.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('value', ty.String(255), nullable = True),
    Column('value_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable = True),
    Column('from_level', ty.Integer, nullable = False, default=0, primary_key = True),
)

t_goalproperties = Table('goalproperties', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False),
    Column('is_variable', ty.Boolean, nullable = False, default=False),
)

t_goals_goalproperties = Table('goals_goalproperties', Base.metadata,
    Column('goal_id', ty.Integer, ForeignKey("goals.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('property_id', ty.Integer, ForeignKey("goalproperties.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('value', ty.String(255), nullable = True),
    Column('value_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable = True),
    Column('from_level', ty.Integer, nullable = False, default=0, primary_key = True),
)

t_rewards = Table('rewards', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False),
)

t_achievements_rewards = Table('achievements_rewards', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), index = True, nullable=False),
    Column('reward_id', ty.Integer, ForeignKey("rewards.id", ondelete="CASCADE"), index = True, nullable=False),
    Column('value', ty.String(255), nullable = True),
    Column('value_translation_id', ty.Integer, ForeignKey("translationvariables.id"), nullable = True),
    Column('from_level', ty.Integer, nullable = False, default=1, index = True)
)

t_achievements_users = Table('achievements_users', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('user_id', ty.BigInteger, ForeignKey("users.id"), index=True, nullable=False),
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('achievement_date', ty.DateTime, nullable=True, index=True),
    Column('level', ty.Integer, default=1, nullable=False, index=True),
    Column('updated_at', ty.DateTime, nullable = False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True),
)

Index("idx_achievements_users_date_not_null_unique",
    t_achievements_users.c.user_id,
    t_achievements_users.c.achievement_id,
    t_achievements_users.c.achievement_date,
    t_achievements_users.c.level,
    unique=True,
    postgresql_where=t_achievements_users.c.achievement_date!=None
)

Index("idx_achievements_users_date_null_unique",
    t_achievements_users.c.user_id,
    t_achievements_users.c.achievement_id,
    t_achievements_users.c.level,
    unique=True,
    postgresql_where=t_achievements_users.c.achievement_date==None
)


t_requirements = Table('requirements', Base.metadata,
    Column('from_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('to_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key = True, nullable=False),
)

t_denials = Table('denials', Base.metadata,
    Column('from_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('to_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key = True, nullable=False),
)

t_languages = Table('languages', Base.metadata,
   Column('id', ty.Integer, primary_key = True),
   Column('name', ty.String(255), nullable = False, index=True),
)

t_translationvariables = Table('translationvariables', Base.metadata,
   Column('id', ty.Integer, primary_key = True),
   Column('name', ty.String(255), nullable = False, index=True),
)

t_translations = Table('translations', Base.metadata,
   Column('id', ty.Integer, primary_key = True),
   Column('translationvariable_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="CASCADE"), nullable = False),
   Column('language_id', ty.Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable = False),
   Column('text', ty.Text(), nullable = False),
)

t_user_device = Table('user_devices', Base.metadata,
    Column('device_id', ty.String(255), primary_key = True),
    Column('user_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('device_os', ty.String, nullable=False),
    Column('push_id', ty.String(255), nullable=False),
    Column('app_version', ty.String(255), nullable=False),
    Column('registered_at', ty.DateTime(), nullable=False, default=datetime.datetime.utcnow),
)

t_user_messages = Table('user_messages', Base.metadata,
    Column('id', ty.BigInteger, primary_key = True),
    Column('user_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index = True, nullable=False),
    Column('translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable = True),
    Column('params', JSON(), nullable=True, default={}),
    Column('is_read', ty.Boolean, index=True, default=False, nullable=False),
    Column('has_been_pushed', ty.Boolean, index=True, default=True, server_default='0', nullable=False),
    Column('created_at', ty.DateTime(), nullable=False, default=datetime.datetime.utcnow, index=True),
)

t_goal_triggers = Table('goal_triggers', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column("name", ty.String(100), nullable=False),
    Column('goal_id', ty.Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('execute_when_complete', ty.Boolean, nullable=False, server_default='0', default=False),
)

t_goal_trigger_steps = Table('goal_trigger_steps', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('goal_trigger_id', ty.Integer, ForeignKey("goal_triggers.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('step', ty.Integer, nullable=False, default=0),
    Column('condition_type', ty.Enum("percentage", name="goal_trigger_condition_types"), default="percentage"),
    Column('condition_percentage', ty.Float, nullable=True),
    Column('action_type', ty.Enum("user_message", name="goal_trigger_action_types"), default="user_message"),
    Column('action_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable = True),

    UniqueConstraint("goal_trigger_id", "step")
)

t_goal_trigger_step_executions = Table('goal_trigger_executions', Base.metadata,
    Column('id', ty.BigInteger, primary_key = True),
    Column('trigger_step_id', ty.Integer, ForeignKey("goal_trigger_steps.id", ondelete="CASCADE"), nullable=False),
    Column('user_id', ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column('execution_level', ty.Integer, nullable = False, default=0),
    Column('execution_date', ty.DateTime(), nullable=False, default=datetime.datetime.utcnow, index=True),
    Column('achievement_date', ty.DateTime(), nullable=True, index=True),
    Index("ix_goal_trigger_executions_combined", "trigger_step_id","user_id","execution_level")
)

class AuthUser(ABase):

    @hybrid_property
    def id(self):
        return self.user_id

    @hybrid_property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self,new_pw):
        if new_pw!=self.password_hash:
            import argon2
            import crypt
            import base64
            self.password_salt = crypt.mksalt()+crypt.mksalt()+crypt.mksalt()+crypt.mksalt()+crypt.mksalt()
            hash = argon2.argon2_hash(new_pw, self.password_salt)
            self.password_hash = base64.b64encode(hash).decode("UTF-8")

    def verify_password(self, pw):
        import argon2
        import base64
        check = base64.b64encode(argon2.argon2_hash(pw, self.password_salt)).decode("UTF-8")
        orig = self.password_hash
        is_valid = check == orig
        return is_valid

    def get_or_create_token(self):
        tokenObj = DBSession.query(AuthToken).filter(and_(
            AuthToken.valid_until>=datetime.datetime.utcnow(),
            AuthToken.user_id == self.user_id
        )).first()

        if not tokenObj:
            token = AuthToken.generate_token()
            tokenObj = AuthToken(
                user_id=self.user_id,
                token=token
            )

            DBSession.add(tokenObj)

        return tokenObj

class AuthToken(ABase):

    @staticmethod
    def generate_token():
        import crypt
        return str(crypt.mksalt()+crypt.mksalt())

    def extend(self):
        self.valid_until = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        DBSession.add(self)

    def __unicode__(self, *args, **kwargs):
        return "Token %s" % (self.id,)

class AuthRole(ABase):
    def __unicode__(self, *args, **kwargs):
        return "Role %s" % (self.name,)

class AuthRolePermission(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.name,)

class UserDevice(ABase):
    def __unicode__(self, *args, **kwargs):
        return "Device: %s" % (self.id,)

    @classmethod
    def add_or_update_device(cls, user_id, device_id, push_id, device_os, app_version):
        update_connection().execute(t_user_device.delete().where(and_(
            t_user_device.c.push_id == push_id,
            t_user_device.c.device_os == device_os
        )))

        device = DBSession.execute(t_user_device.select().where(and_(
            t_user_device.c.device_id == device_id,
            t_user_device.c.user_id == user_id
        ))).fetchone()
        if device and (device["push_id"] != push_id
            or device["device_os"] != device_os
            or device["app_version"] != app_version
        ):
            uSession = update_connection()
            q = t_user_device.update().values({
                "push_id": push_id,
                "device_os": device_os,
                "app_version": app_version
            }).where(and_(
                t_user_device.c.device_id == device_id,
                t_user_device.c.user_id == user_id
            ))
            uSession.execute(q)
        elif not device:  # insert
            uSession = update_connection()
            q = t_user_device.insert().values({
                "push_id": push_id,
                "device_os": device_os,
                "app_version": app_version,
                "device_id": device_id,
                "user_id": user_id
            })
            uSession.execute(q)

class User(ABase):
    """A user participates in the gamification, i.e. can get achievements, rewards, participate in leaderbaord etc."""

    def __unicode__(self, *args, **kwargs):
        return "User %s" % (self.id,)

    def __init__(self, *args, **kw):
        """ create a user object

        Each user has a timezone and a location to support time- and geo-aware gamification.
        There is also a friends-relation for leaderboards and a groups-relation.
        """
        ABase.__init__(self, *args, **kw)

    #TODO:Cache
    @classmethod
    def get_user(cls,user_id):
        return DBSession.execute(t_users.select().where(t_users.c.id==user_id)).fetchone()

    @classmethod
    def get_users(cls, user_ids):
        return {
            x["id"] : x for x in
            DBSession.execute(t_users.select().where(t_users.c.id.in_(user_ids))).fetchall()
        }

    @classmethod
    def get_cache_expiration_time_for_today(cls,user):
        """return the seconds until the day of the user ends (timezone of the user).

        This is needed as achievements may be limited to a specific time (e.g. only during holidays)."""

        tzobj = pytz.timezone(user["timezone"])
        now = datetime.datetime.now(tzobj)
        today = now.replace(hour=0,minute=0,second=0,microsecond=0)
        tomorrow = today+timedelta(days=1)
        return int((tomorrow-today).total_seconds())

    @classmethod
    def set_infos(cls,user_id,lat,lng,timezone,country,region,city,language,friends, groups, additional_public_data):
        """set the user's metadata like friends,location and timezone"""


        new_friends_set = set(friends)
        existing_users_set = {x["id"] for x in DBSession.execute(select([t_users.c.id]).where(t_users.c.id.in_([user_id,]+friends))).fetchall()}
        existing_friends = {x["to_id"] for x in DBSession.execute(select([t_users_users.c.to_id]).where(t_users_users.c.from_id==user_id)).fetchall()}
        friends_to_create = (new_friends_set-existing_users_set-{user_id,})
        friends_to_append = (new_friends_set-existing_friends)
        friends_to_delete = (existing_friends-new_friends_set)

        new_groups_set = set(groups)
        existing_groups_set = {x["id"] for x in DBSession.execute(select([t_groups.c.id]).where(t_groups.c.id.in_(groups))).fetchall()}
        existing_groups_of_user = {x["group_id"] for x in DBSession.execute(select([t_users_groups.c.group_id]).where(t_users_groups.c.user_id==user_id)).fetchall()}
        groups_to_create = (new_groups_set-existing_groups_set)
        groups_to_append = (new_groups_set-existing_groups_of_user)
        groups_to_delete = (existing_groups_of_user-new_groups_set)

        #add or select user
        if user_id in existing_users_set:
            user = DBSession.query(User).filter_by(id=user_id).first()
        else:
            user = User()

        user.id = user_id
        user.lat = lat
        user.lng = lng
        user.timezone = timezone
        user.country = country
        user.region = region
        user.city = city
        user.additional_public_data = additional_public_data

        language = DBSession.execute(t_languages.select().where(t_languages.c.name == language)).fetchone()
        if language:
            user.language_id = language["id"]
        else:
            user.language_id = None

        DBSession.add(user)
        DBSession.flush()

        #FRIENDS

        #insert missing friends in user table
        if len(friends_to_create)>0:
            update_connection().execute(t_users.insert(), [{"id":f} for f in friends_to_create])

        #delete old friends
        if len(friends_to_delete)>0:
            update_connection().execute(t_users_users.delete().where(and_(t_users_users.c.from_id==user_id,
                                                            t_users_users.c.to_id.in_(friends_to_delete))))

        #insert missing friends
        if len(friends_to_append)>0:
            update_connection().execute(t_users_users.insert(),[{"from_id":user_id,"to_id":f} for f in friends_to_append])

        #GROUPS

        #insert missing groups in group table
        if len(groups_to_create)>0:
            update_connection().execute(t_groups.insert(), [{"id":f} for f in groups_to_create])

        #delete old groups of user
        if len(groups_to_delete)>0:
            update_connection().execute(t_users_groups.delete().where(and_(t_users_groups.c.user_id==user_id,
                                                                          t_users_groups.c.group_id.in_(groups_to_delete))))

        #insert missing groups of user
        if len(groups_to_append)>0:
            update_connection().execute(t_users_groups.insert(),[{"user_id":user_id,"group_id":f} for f in groups_to_append])

    @classmethod
    def delete_user(cls,user_id):
        """delete a user including all dependencies."""
        update_connection().execute(t_achievements_users.delete().where(t_achievements_users.c.user_id==user_id))
        update_connection().execute(t_goal_evaluation_cache.delete().where(t_goal_evaluation_cache.c.user_id==user_id))
        update_connection().execute(t_users_users.delete().where(t_users_users.c.to_id==user_id))
        update_connection().execute(t_users_users.delete().where(t_users_users.c.from_id==user_id))
        update_connection().execute(t_users_groups.delete().where(t_users_groups.c.user_id==user_id))
        update_connection().execute(t_values.delete().where(t_values.c.user_id==user_id))
        update_connection().execute(t_users.delete().where(t_users.c.id==user_id))

    @classmethod
    def basic_output(cls, user):
        return {
            "id" : user["id"],
            "additional_public_data" : user["additional_public_data"]
        }

    @classmethod
    def full_output(cls, user_id):

        user = DBSession.execute(t_users.select().where(t_users.c.id == user_id)).fetchone()

        j = t_users.join(t_users_users,t_users_users.c.to_id == t_users.c.id)
        friends = DBSession.execute(t_users.select(from_obj=j).where(t_users_users.c.from_id == user_id)).fetchall()

        j = t_groups.join(t_users_groups)
        groups = DBSession.execute(t_groups.select(from_obj=j).where(t_users_groups.c.user_id== user_id)).fetchall()

        language = get_settings().get("fallback_language","en")
        j = t_users.join(t_languages)
        user_language = DBSession.execute(select([t_languages.c.name], from_obj=j).where(t_users.c.id == user_id)).fetchone()
        if user_language:
            language = user_language["name"]

        ret = {
            "id" : user["id"],
            "lat" : user["lat"],
            "lng" : user["lng"],
            "timezone" : user["timezone"],
            "language": language,
            "country": user["country"],
            "region": user["region"],
            "city": user["city"],
            "created_at": user["created_at"],
            "additional_public_data": user["additional_public_data"],
            "friends" : [User.basic_output(f) for f in friends],
            "groups": [Group.basic_output(g) for g in groups],
        }

        if get_settings().get("enable_user_authentication"):
            auth_user = DBSession.execute(t_auth_users.select().where(t_auth_users.c.user_id == user_id)).fetchone()
            if auth_user:
                ret.update({
                    "email" : auth_user["email"]
                })

        return ret

class Group(ABase):
    def __unicode__(self, *args, **kwargs):
        return "(ID: %s)" % (self.id,)

    @classmethod
    def basic_output(cls, group):
        return {
            "id" : group["id"]
        }

class Variable(ABase):
    """A Variable is anything that should be meassured in your application and be used in :class:`.Goal`.

       To save database rows, variables may be grouped by time:
       group needs to be set to "year","month","week","day","timeslot" or "none" (default)
    """

    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

    @classmethod
    @cache_general.cache_on_arguments()
    def get_variable_by_name(cls,name):
        return DBSession.execute(t_variables.select(t_variables.c.name==name)).fetchone()

    @classmethod
    def get_datetime_for_tz_and_group(cls,tz,group,at_datetime=None):
        """
            get the datetime of the current row, needed for grouping
            the optional parameter at_datetime can provide a timezone-aware datetime which overrides the default "now"
        """
        tzobj = pytz.timezone(tz)


        if not at_datetime:
            now = datetime.datetime.now(tzobj)
        else:
            now = at_datetime

        t = None
        if group=="year":
            t = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif group=="month":
            t = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif group=="week":
            t = now-datetime.timedelta(days=now.weekday())
            t = t.replace(hour=0, minute=0, second=0, microsecond=0)
        elif group=="day":
            t = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif group=="none":
            t = now
        else:
            #return datetime.datetime.max.replace
            return datetime.datetime(year=2000,month=1,day=1,hour=0,minute=0,second=0,microsecond=0).replace(tzinfo=pytz.utc)


        return t.astimezone(tzobj)

    @classmethod
    @cache_general.cache_on_arguments()
    def map_variables_to_rules(cls):
        """return a map from variable_ids to {"goal":goal_obj,"achievement":achievement_obj} dictionaries.

        Used to know which goals need to be reevaluated after a value for the variable changes.
        """
        q = select([t_goals,t_variables.c.id.label("variable_id")])\
            .where(or_(t_goals.c.condition.ilike(func.concat('%"',t_variables.c.name,'"%')),
                       t_goals.c.condition.ilike(func.concat("%'",t_variables.c.name,"'%"))))
        m={}
        for row in DBSession.execute(q).fetchall():
            if not row["variable_id"] in m:
                m[row["variable_id"]] = []

            m[row["variable_id"]].append({"goal":row,"achievement":Achievement.get_achievement(row["achievement_id"])})
        return m

    @classmethod
    def invalidate_caches_for_variable_and_user(cls, variable_id, user_id, dt):
        """ invalidate the relevant caches for this user and all relevant users with concerned leaderboards"""
        goalsandachievements = cls.map_variables_to_rules().get(variable_id, [])

        Goal.clear_goal_caches(user_id, [
            (entry["goal"]["id"], Achievement.get_datetime_for_evaluation_type(entry["achievement"]["evaluation_timezone"], entry["achievement"]["evaluation"], dt=dt))
                for entry in goalsandachievements
            ]
        )
        for entry in goalsandachievements:
            achievement_date = Achievement.get_datetime_for_evaluation_type(entry["achievement"]["evaluation_timezone"], entry["achievement"]["evaluation"],dt=dt)
            Achievement.invalidate_evaluate_cache(user_id, entry["achievement"], achievement_date)

    @classmethod
    def may_increase(cls, variable_row, request, user_id):
        if not asbool(get_settings().get("enable_user_authentication", False)):
            #Authentication deactivated
            return True
        if request.has_perm(perm_global_increase_value):
            # I'm the global admin
            return True
        if variable_row["increase_permission"]=="own" and request.user and str(request.user.id)==str(user_id):
            #The variable may be updated for myself
            return True
        return False


class Value(ABase):
    """A Value describes the relation of the user to a variable.

    (e.g. it counts the occurences of the "events" which the variable represents) """


    @classmethod
    def increase_value(cls, variable_name, user, value, key, at_datetime=None):
        """increase the value of the variable for the user.

        In addition to the variable_name there may be an application-specific key which can be used in your :class:`.Goal` definitions
        The parameter at_datetime is optional and can specify a timezone-aware datetime to define when the event happened
        """

        user_id = user["id"]
        tz = user["timezone"]

        variable = Variable.get_variable_by_name(variable_name)
        dt = Variable.get_datetime_for_tz_and_group(tz, variable["group"], at_datetime=at_datetime)

        key = '' if key is None else str(key)

        condition = and_(t_values.c.datetime == dt,
                         t_values.c.variable_id == variable["id"],
                         t_values.c.user_id == user_id,
                         t_values.c.key == key)

        current_value = DBSession.execute(select([t_values.c.value,]).where(condition)).scalar()
        if current_value is not None:
            update_connection().execute(t_values.update(condition, values={"value":current_value+value}))
        else:
            update_connection().execute(t_values.insert({"datetime": dt,
                                           "variable_id": variable["id"],
                                           "user_id": user_id,
                                           "key": key,
                                           "value": value}))

        Variable.invalidate_caches_for_variable_and_user(variable_id=variable["id"], user_id=user["id"], dt = dt)
        new_value = DBSession.execute(select([t_values.c.value, ]).where(condition)).scalar()
        return new_value

class AchievementCategory(ABase):
    """A category for grouping achievement types"""

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievementcategory(cls,achievementcategory_id):
        return DBSession.execute(t_achievementcategories.select().where(t_achievementcategories.c.id==achievementcategory_id)).fetchone()

    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

class Achievement(ABase):
    """A collection of goals which has multiple :class:`AchievementProperty` and :class:`Reward`."""

    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievement(cls,achievement_id):
        return DBSession.execute(t_achievements.select().where(t_achievements.c.id==achievement_id)).fetchone()

    @classmethod
    def get_achievements_by_user_for_today(cls,user):
        """Returns all achievements that are relevant for the user today.

        This is needed as achievements may be limited to a specific time (e.g. only during holidays)
        """

        def generate_achievements_by_user_for_today():
            today = datetime.date.today()
            by_loc = {x["id"] : x["distance"] for x in cls.get_achievements_by_location(coords(user))}
            by_date = cls.get_achievements_by_date(today)
            def update(arr,distance):
                arr["distance"]=distance
                return arr

            return [update(arr,by_loc[arr["id"]]) for arr in by_date if arr["id"] in by_loc]

        key = str(user["id"])
        expiration_time = User.get_cache_expiration_time_for_today(user)

        return cache_achievements_by_user_for_today.get_or_create(key,generate_achievements_by_user_for_today, expiration_time=expiration_time)

    #We need to fetch all achievement data in one of these methods -> by_date is just queried once a date

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievements_by_location(cls,latlng):
        """return achievements which are valid in that location."""
        #TODO: invalidate automatically when achievement in user's range is modified
        distance = calc_distance(latlng, (t_achievements.c.lat, t_achievements.c.lng)).label("distance")
        q = select([t_achievements.c.id,
                    distance])\
            .where(or_(and_(t_achievements.c.lat==None,t_achievements.c.lng==None),
                        distance < t_achievements.c.max_distance))

        return [dict(x.items()) for x in DBSession.execute(q).fetchall() if len(Goal.get_goals(x['id'])) > 0]

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievements_by_date(cls,date):
        """return achievements which are valid at that date"""
        q = t_achievements.select().where(and_(or_(t_achievements.c.valid_start==None,
                                                          t_achievements.c.valid_start<=date),
                                               or_(t_achievements.c.valid_end==None,
                                                          t_achievements.c.valid_end>=date)
                                               ))

        return [dict(x.items()) for x in DBSession.execute(q).fetchall() if len(Goal.get_goals(x['id']))>0]

    #TODO:CACHE
    @classmethod
    def get_relevant_users_by_achievement_and_user(cls,achievement,user_id):
        """return all relevant other users for the leaderboard.

        depends on the "relevance" attribute of the achivement, can be "friends" or "city" (city is still a todo)
        """
        # this is needed to compute the leaderboards
        users=[user_id,]
        if achievement["relevance"]=="city":
            #TODO
            pass
        elif achievement["relevance"]=="friends":
            users += [x["to_id"] for x in DBSession.execute(select([t_users_users.c.to_id,], t_users_users.c.from_id==user_id)).fetchall()]
        elif achievement["relevance"] == "global":
            users += [x.id for x in DBSession.execute(select([t_users.c.id,])).fetchall()]
        return set(users)

    #TODO:CACHE
    @classmethod
    def get_relevant_users_by_achievement_and_user_reverse(cls,achievement,user_id):
        """return all users which have this user as friends and are relevant for this achievement.

        the reversed version is needed to know in whose contact list the user is. when the user's value is updated, all the leaderboards of these users need to be regenerated"""
        users=[user_id,]
        if achievement["relevance"]=="city":
            #TODO
            pass
        elif achievement["relevance"]=="friends":
            users += [x["from_id"] for x in DBSession.execute(select([t_users_users.c.from_id,], t_users_users.c.to_id==user_id)).fetchall()]
        elif achievement["relevance"] == "global":
            users += [x.id for x in DBSession.execute(select([t_users.c.id, ])).fetchall()]
        return set(users)

    @classmethod
    def get_level(cls, user_id, achievement_id, achievement_date):
        """get the current level of the user for this achievement."""

        def generate():
            q = select([t_achievements_users.c.level,
                        t_achievements_users.c.achievement_date,
                        t_achievements_users.c.updated_at],
                           and_(t_achievements_users.c.user_id==user_id,
                                t_achievements_users.c.achievement_date== achievement_date,
                                t_achievements_users.c.achievement_id==achievement_id)).order_by(t_achievements_users.c.level.desc())
            return [x for x in DBSession.execute(q).fetchall()]

        return cache_achievements_users_levels.get_or_create("%s_%s_%s" % (user_id,achievement_id,achievement_date),generate)

    @classmethod
    def get_level_int(cls,user_id,achievement_id,achievement_date):
        """get the current level of the user for this achievement as int (0 if the user does not have this achievement)"""
        lvls = Achievement.get_level(user_id, achievement_id,achievement_date)
        if not lvls:
            return 0
        else:
            return lvls[0]["level"]

    @classmethod
    def basic_output(cls,achievement,goals,include_levels=True,
                     max_level_included=None):
        """construct the basic basic_output structure for the achievement."""

        achievementcategory = None
        if achievement["achievementcategory_id"]!=None:
            achievementcategory = AchievementCategory.get_achievementcategory(achievement["achievementcategory_id"])

        out = {
            "id" : achievement["id"],
            "view_permission" : achievement["view_permission"],
            "internal_name" : achievement["name"],
            "maxlevel" : achievement["maxlevel"],
            "priority" : achievement["priority"],
            "hidden" : achievement["hidden"],
            "achievementcategory" : achievementcategory["name"] if achievementcategory!=None else ""
            #"updated_at" : combine_updated_at([achievement["updated_at"],]),
        }

        if include_levels:
            levellimit = achievement["maxlevel"]
            if max_level_included:
                max_level_included = min(max_level_included,levellimit)

            out["levels"] = {
                str(i) : {
                    "level" : i,
                    "goals" : { str(g["id"]) : Goal.basic_goal_output(g,i) for g in goals},
                    "rewards" : {str(r["id"]) : {
                        "id" : r["id"],
                        "reward_id" : r["reward_id"],
                        "name" : r["name"],
                        "value" : evaluate_string(r["value"], {"level":i}),
                        "value_translated" : Translation.trs(r["value_translation_id"], {"level":i}),
                    } for r in Achievement.get_rewards(achievement["id"],i)},
                    "properties" : {str(r["property_id"]) : {
                        "property_id" : r["property_id"],
                        "name" : r["name"],
                        "value" : evaluate_string(r["value"], {"level":i}),
                        "value_translated" : Translation.trs(r["value_translation_id"], {"level":i}),
                    } for r in Achievement.get_achievement_properties(achievement["id"],i)}
            } for i in range(1,max_level_included+1)}
        return out

    @classmethod
    def evaluate(cls, user, achievement_id, achievement_date, execute_triggers=True):
        """evaluate the achievement including all its subgoals for the user.

           return the basic_output for the achievement plus information about the new achieved levels
        """
        def generate():
            achievement = Achievement.get_achievement(achievement_id)

            user_id = user["id"]
            user_ids = Achievement.get_relevant_users_by_achievement_and_user(achievement, user_id)

            user_has_level = Achievement.get_level_int(user_id, achievement["id"], achievement_date)
            user_wants_level = min((user_has_level or 0)+1, achievement["maxlevel"])

            goal_evals={}
            all_goals_achieved = True
            goals = Goal.get_goals(achievement["id"])
            for goal in goals:
                goal_eval = Goal.get_goal_eval_cache(goal["id"], achievement_date, user_id)
                if not goal_eval:
                    Goal.evaluate(goal, achievement, achievement_date, user, user_wants_level,None, execute_triggers=execute_triggers)
                    goal_eval = Goal.get_goal_eval_cache(goal["id"], achievement_date, user_id)

                if achievement["relevance"]=="friends" or achievement["relevance"]=="city" or achievement["relevance"]=="global":
                    goal_eval["leaderboard"] = Goal.get_leaderboard(goal, achievement_date, user_ids)
                    own_filter = list(filter(lambda x: x["user"]["id"] == user_id, goal_eval["leaderboard"]))
                    if len(own_filter)>0:
                        goal_eval["leaderboard_position"] = own_filter[0]["position"]
                    else:
                        goal_eval["leaderboard_position"] = None

                goal_evals[goal["id"]]=goal_eval
                if not goal_eval["achieved"]:
                    all_goals_achieved = False

            output = ""
            new_level_output = None
            full_output = True # will be false, if the full basic_output is generated in a recursion step

            if all_goals_achieved and user_has_level < achievement["maxlevel"]:
                #NEW LEVEL YEAH!

                new_level_output = {
                    "rewards" : {
                        str(r["id"]) : {
                            "id" : r["id"],
                            "reward_id" : r["reward_id"],
                            "name" : r["name"],
                            "value" : evaluate_string(r["value"], {"level":user_wants_level}),
                            "value_translated" : Translation.trs(r["value_translation_id"], {"level":user_wants_level}),
                        } for r in Achievement.get_rewards(achievement["id"],user_wants_level)
                     },
                    "properties" : {
                        str(r["property_id"]) : {
                            "property_id" : r["property_id"],
                            "name" : r["name"],
                            "is_variable" : r["is_variable"],
                            "value" : evaluate_string(r["value"], {"level":user_wants_level}),
                            "value_translated" : Translation.trs(r["value_translation_id"], {"level":user_wants_level})
                        } for r in Achievement.get_achievement_properties(achievement["id"],user_wants_level)
                    },
                    "level" : user_wants_level
                }

                for prop in new_level_output["properties"].values():
                    if prop["is_variable"]:
                        Value.increase_value(prop["name"], user, prop["value"], achievement_id)

                update_connection().execute(t_achievements_users.insert().values({
                    "user_id" : user_id,
                    "achievement_id" : achievement["id"],
                    "achievement_date" : achievement_date,
                    "level" : user_wants_level
                }))

                #invalidate getter
                cache_achievements_users_levels.delete("%s_%s_%s" % (user_id,achievement_id,achievement_date))

                user_has_level = user_wants_level
                user_wants_level = user_wants_level+1

                Goal.clear_goal_caches(user_id, [(g["goal_id"],achievement_date) for g in goal_evals.values()])
                #the level has been updated, we need to do recursion now...
                #but only if there are more levels...
                if user_has_level < achievement["maxlevel"]:
                    output = generate()
                    full_output = False

            if full_output: #is executed, if this is the last recursion step
                output = Achievement.basic_output(achievement,goals,True,max_level_included=user_has_level+1)
                output.update({
                   "level" : user_has_level,
                   "levels_achieved" : {
                        str(x["level"]) : x["updated_at"] for x in Achievement.get_level(user_id, achievement["id"], achievement_date)
                    },
                   "maxlevel" : achievement["maxlevel"],
                   "new_levels" : {},
                   "goals":goal_evals,
                   "achievement_date": achievement_date,
                   #"updated_at":combine_updated_at([achievement["updated_at"],] + [g["updated_at"] for g in goal_evals])
                })

            if new_level_output is not None: #if we reached a new level in this recursion step, add the previous levels rewards and properties
                output["new_levels"][str(user_has_level)]=new_level_output

            return output

        #TODO ACHIEVEMENT
        return cache_achievement_eval.get_or_create("%s_%s_%s" % (user["id"],achievement_id,achievement_date),generate)

    @classmethod
    def invalidate_evaluate_cache(cls,user_id,achievement, achievement_date):
        """invalidate the evaluation cache for all goals of this achievement for the user."""

        #We neeed to invalidate for all relevant users because of the leaderboards
        for uid in Achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user_id):
            cache_achievement_eval.delete("%s_%s_%s" % (uid, achievement["id"], achievement_date))

    @classmethod
    @cache_general.cache_on_arguments()
    def get_rewards(cls,achievement_id,level):
        """return the new rewards which are given for the achievement level."""

        this_level = DBSession.execute(select([t_rewards.c.id.label("reward_id"),
                                               t_achievements_rewards.c.id,
                                               t_rewards.c.name,
                                               t_achievements_rewards.c.from_level,
                                               t_achievements_rewards.c.value,
                                               t_achievements_rewards.c.value_translation_id],
                                              from_obj=t_rewards.join(t_achievements_rewards))\
                                       .where(and_(or_(t_achievements_rewards.c.from_level<=level,
                                                     t_achievements_rewards.c.from_level==None),
                                                 t_achievements_rewards.c.achievement_id==achievement_id))\
                                       .order_by(t_achievements_rewards.c.from_level))\
                                       .fetchall()

        prev_level = DBSession.execute(select([t_rewards.c.id.label("reward_id"),
                                               t_achievements_rewards.c.id,
                                               t_achievements_rewards.c.value,
                                               t_achievements_rewards.c.value_translation_id],
                                              from_obj=t_rewards.join(t_achievements_rewards))\
                                       .where(and_(or_(t_achievements_rewards.c.from_level<=level-1,
                                                     t_achievements_rewards.c.from_level==None),
                                                 t_achievements_rewards.c.achievement_id==achievement_id))\
                                       .order_by(t_achievements_rewards.c.from_level))\
                                       .fetchall()

        #now compute the diff :-/
        build_hash = lambda x,l : hashlib.md5((str(x["id"])+str(evaluate_string(x["value"], {"level":l}))+str(Translation.trs(x["value_translation_id"], {"level":l}))).encode("UTF-8")).hexdigest()
        prev_hashes = {build_hash(x,level-1) for x in prev_level}
        #this_hashes = {build_hash(x,level) for x in this_level}

        retlist = [x for x in this_level if not build_hash(x,level) in prev_hashes]
        return retlist

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievement_properties(cls,achievement_id,level):
        """return all properties which are associated to the achievement level."""
        result = DBSession.execute(select([t_achievementproperties.c.id.label("property_id"),
                                         t_achievementproperties.c.name,
                                         t_achievementproperties.c.is_variable,
                                         t_achievements_achievementproperties.c.from_level,
                                         t_achievements_achievementproperties.c.value,
                                         t_achievements_achievementproperties.c.value_translation_id],
                                        from_obj=t_achievementproperties.join(t_achievements_achievementproperties))\
                                 .where(and_(or_(t_achievements_achievementproperties.c.from_level<=level,
                                                 t_achievements_achievementproperties.c.from_level==None),
                                             t_achievements_achievementproperties.c.achievement_id==achievement_id))\
                                 .order_by(t_achievements_achievementproperties.c.from_level))\
                        .fetchall()

        return DBSession.execute(select([t_achievementproperties.c.id.label("property_id"),
                                         t_achievementproperties.c.name,
                                         t_achievementproperties.c.is_variable,
                                         t_achievements_achievementproperties.c.from_level,
                                         t_achievements_achievementproperties.c.value,
                                         t_achievements_achievementproperties.c.value_translation_id],
                                        from_obj=t_achievementproperties.join(t_achievements_achievementproperties))\
                                 .where(and_(or_(t_achievements_achievementproperties.c.from_level<=level,
                                                 t_achievements_achievementproperties.c.from_level==None),
                                             t_achievements_achievementproperties.c.achievement_id==achievement_id))\
                                 .order_by(t_achievements_achievementproperties.c.from_level))\
                        .fetchall()

    @classmethod
    def get_datetime_for_evaluation_type(cls, evaluation_timezone, evaluation_type, dt=None):
        """
            This computes the datetime to identify the time of the achievement.
            Only relevant for repeating achievements (monthly, yearly, weekly, daily)
            Returns None for all other achievement types
        """

        if evaluation_type and not evaluation_timezone:
            evaluation_timezone = "UTC"

        tzobj = pytz.timezone(evaluation_timezone)
        if not dt:
            dt = datetime.datetime.now(tzobj)

        else:
            dt = dt.astimezone(tzobj)

        t = None
        if evaluation_type == "yearly":
            t = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif evaluation_type == "monthly":
            t = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif evaluation_type == "weekly":
            t = dt - datetime.timedelta(days=dt.weekday())
            t = t.replace(hour=0, minute=0, second=0, microsecond=0)
        elif evaluation_type == "daily":
            t = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif evaluation_type == "immediately":
            return None
        elif evaluation_type == "end":
            return None

        return t.astimezone(tzobj)


class AchievementProperty(ABase):
    """A AchievementProperty describes the :class:`Achievement`s of our system.

    Examples: name, image, description, xp

    Additionally Properties can be used as variables.
    This is useful to model goals like "reach 1000xp"

    """
    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

class AchievementAchievementProperty(ABase):
    """A poperty value for an :class:`Achievement`"""
    pass

class GoalProperty(ABase):
    """A goalproperty describes the :class:`Goal`s of our system.

    Examples: name, image, description, xp

    Additionally Properties can be used as variables.
    This is useful to model goals like "reach 1000xp"

    """
    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

class GoalGoalProperty(ABase):
    """A goalpoperty value for a :class:`Goal`"""
    pass

class Reward(ABase):
    """Rewards are given when reaching :class:`Achievement`s.

    Examples: badge, item
    """
    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

class AchievementReward(ABase):
    """A Reward value for an :class:`Achievement` """

    @classmethod
    def get_achievement_reward(cls, achievement_reward_id):
        return DBSession.execute(t_achievements_rewards.select(t_achievements_rewards.c.id==achievement_reward_id)).fetchone()

class AchievementUser(ABase):
    """Relation between users and achievements, contains level and updated_at date"""
    pass

class GoalEvaluationCache(ABase):
    """Cache for the evaluation of goals for users"""
    pass

class Goal(ABase):
    """A Goal defines a rule on variables that needs to be reached to get achievements"""

    def __unicode__(self, *args, **kwargs):
        if self.name_translation_id!=None:
            name = Translation.trs(self.name_translation.id, {"level":1, "goal":'0'})[get_settings().get("fallback_language","en")]
            return str(name) + " (ID: %s)" % (self.id,)
        else:
            return self.name + " (ID: %s)" % (self.id,)

    @classmethod
    @cache_general.cache_on_arguments()
    def get_goals(cls,achievement_id):
        return DBSession.execute(t_goals.select(t_goals.c.achievement_id==achievement_id)).fetchall()

    @classmethod
    def compute_progress(cls, goal, achievement, user, evaluation_date):
        """computes the progress of the goal for the given user_id

        goal attributes:
            - goal:                the value that is used for comparison
            - operator:            "geq" or "leq"; used for comparison
            - condition:           the rule as python code
            - group_by_dateformat: passed as a parameter to to_char ( http://www.postgresql.org/docs/9.3/static/functions-formatting.html )
                                   e.g. you can select and group by the weekday by using "ID" for ISO 8601 day of the week (1-7) which can afterwards be used in the condition

            - group_by_key:        group by the key of the values table
            - timespan:            number of days which are considered (uses utc, i.e. days*24hours)
            - maxmin:              "max" or "min" - select min or max value after grouping
            - evaluation:          "daily", "weekly", "monthly", "yearly" evaluation (users timezone)

        """

        user_id = user["id"]
        timezone = achievement["evaluation_timezone"]

        def generate_statement_cache():
            condition = evaluate_condition(goal["condition"], column_variable = t_variables.c.name.label("variable_name"),
                                                              column_key = t_values.c.key)
            group_by_dateformat = goal["group_by_dateformat"]
            group_by_key = goal["group_by_key"]
            timespan = goal["timespan"]
            maxmin = goal["maxmin"]
            evaluation_type = achievement["evaluation"]

            #prepare
            select_cols=[func.sum(t_values.c.value).label("value"),
                         t_values.c.user_id]

            j = t_values.join(t_variables)

            #    # We need to access the user's timezone later
            j = j.join(t_users)

            datetime_col=None
            if group_by_dateformat:
                # here we need to convert to users' time zone, as we might need to group by e.g. USER's weekday
                if timezone:
                    datetime_col = func.to_char(text("values.datetime AT TIME ZONE '%s'" % (timezone,)), group_by_dateformat).label("datetime")
                else:
                    datetime_col = func.to_char(text("values.datetime AT TIME ZONE users.timezone"),
                                                group_by_dateformat).label("datetime")
                select_cols.append(datetime_col)

            if group_by_key:
                select_cols.append(t_values.c.key)

            #build query
            q = select(select_cols,
                       from_obj=j)\
               .where(t_values.c.user_id==bindparam("user_id"))\
               .group_by(t_values.c.user_id)

            if condition is not None:
                q = q.where(condition)

            if timespan:
                #here we can use the utc time
                q = q.where(t_values.c.datetime>=datetime.datetime.utcnow()-datetime.timedelta(days=timespan))

            if evaluation_type!="immediately":

                achievement_date = Achievement.get_datetime_for_evaluation_type(timezone, evaluation_type, evaluation_date)
                if evaluation_type=="daily":
                    q = q.where(and_(
                        t_values.c.datetime >= achievement_date,
                        t_values.c.datetime < achievement_date + datetime.timedelta(days=1))
                    )
                elif evaluation_type=="weekly":
                    q = q.where(and_(
                        t_values.c.datetime >= achievement_date,
                        t_values.c.datetime < achievement_date + datetime.timedelta(days=7))
                    )
                elif evaluation_type=="monthly":
                    next_month = Achievement.get_datetime_for_evaluation_type(timezone, "monthly", achievement_date + datetime.timedelta(days=32))
                    q = q.where(and_(
                        t_values.c.datetime >= achievement_date,
                        t_values.c.datetime < next_month)
                    )
                elif evaluation_type=="yearly":
                    next_year = Achievement.get_datetime_for_evaluation_type(timezone, "yearly", achievement_date + datetime.timedelta(days=366))
                    q = q.where(and_(
                        t_values.c.datetime >= achievement_date,
                        t_values.c.datetime < next_year)
                    )
                elif evaluation_type == "end":
                    pass
                    #Todo implement for end

            if datetime_col is not None or group_by_key is not False:
                if datetime_col is not None:
                    q = q.group_by(datetime_col)

                if group_by_key is not False:
                    q = q.group_by(t_values.c.key)
                query_with_groups = q.alias()

                select_cols2 = [query_with_groups.c.user_id]

                if maxmin=="min":
                    select_cols2.append(func.min(query_with_groups.c.value).label("value"))
                else:
                    select_cols2.append(func.max(query_with_groups.c.value).label("value"))

                combined_user_query = select(select_cols2,from_obj=query_with_groups)\
                                      .group_by(query_with_groups.c.user_id)

                return combined_user_query
            else:
                return q

        #q = cache_goal_statements.get_or_create(str(goal["id"]),generate_statement_cache)
        # TODO: Cache the statement / Make it serializable for caching in redis
        q = generate_statement_cache()

        return DBSession.execute(q, {'user_id' : user_id})

    @classmethod
    def evaluate(cls, goal, achievement, achievement_date, user, level, goal_eval_cache_before=False, execute_triggers=True):
        """evaluate the goal for the user_ids and the level"""

        operator = goal["operator"]

        #TODO: Move this call to outer loops
        user_id = user["id"]

        users_progress = Goal.compute_progress(goal, achievement, user, achievement_date)
        goal_evaluation = {e["user_id"] : e["value"] for e in users_progress}
        goal_achieved = False

        if goal_eval_cache_before is False:
            goal_eval_cache_before = cls.get_goal_eval_cache(goal["id"], achievement_date, user_id)

        new = goal_evaluation.get(user_id,0.0)

        if goal_eval_cache_before is None or goal_eval_cache_before.get("value",0.0)!=goal_evaluation.get(user_id,0.0):

            #Level is the next level, or the current level if I'm alread at max
            params = {
                "level" : level
            }
            goal_goal = evaluate_value_expression(goal["goal"], params)
            if goal_goal is not None and operator=="geq" and new>=goal_goal:
                goal_achieved = True
                new = min(new,goal_goal)

            elif goal_goal is not None and operator=="leq" and new<=goal_goal:
                goal_achieved = True
                new = max(new,goal_goal)

            previous_goal = Goal.basic_goal_output(goal, level-1).get("goal_goal",0)
            # Evaluate triggers
            if execute_triggers:
                Goal.select_and_execute_triggers(
                    goal = goal,
                    achievement_date = achievement_date,
                    user_id = user_id,
                    level = level,
                    current_goal = goal_goal,
                    previous_goal = previous_goal,
                    value = new
                )

            return Goal.set_goal_eval_cache(goal=goal,
                                            user_id=user_id,
                                            achievement_date=achievement_date,
                                            value=new,
                                            achieved = goal_achieved)
        else:
            return Goal.get_goal_eval_cache(goal["id"], achievement_date, user_id)

    @classmethod
    def select_and_execute_triggers(cls, goal, achievement_date, user_id, level, current_goal, value, previous_goal):

        if previous_goal == current_goal:
            previous_goal = 0.0

        j = t_goal_trigger_step_executions.join(t_goal_trigger_steps)
        executions = {r["goal_trigger_id"] : r["step"] for r in
                      DBSession.execute(
                          select([t_goal_trigger_steps.c.id.label("step_id"),
                                  t_goal_trigger_steps.c.goal_trigger_id,
                                  t_goal_trigger_steps.c.step], from_obj=j).\
                          where(and_(t_goal_triggers.c.goal_id == goal["id"],
                                     t_goal_trigger_step_executions.c.achievement_date == achievement_date,
                                     t_goal_trigger_step_executions.c.user_id == user_id,
                                     t_goal_trigger_step_executions.c.execution_level == level))).fetchall()
                      }

        j = t_goal_trigger_steps.join(t_goal_triggers)

        trigger_steps = DBSession.execute(select([
            t_goal_trigger_steps.c.id,
            t_goal_trigger_steps.c.goal_trigger_id,
            t_goal_trigger_steps.c.step,
            t_goal_trigger_steps.c.condition_type,
            t_goal_trigger_steps.c.condition_percentage,
            t_goal_trigger_steps.c.action_type,
            t_goal_trigger_steps.c.action_translation_id,
            t_goal_triggers.c.execute_when_complete,
        ],from_obj=j).\
        where(t_goal_triggers.c.goal_id == goal["id"],)).fetchall()

        trigger_steps = [s for s in trigger_steps if s["step"]>executions.get(s["goal_trigger_id"],-sys.maxsize)]

        exec_queue = {}

        #When editing things here, check the insert_trigger_step_executions_after_step_upsert event listener too!!!!!!!
        if len(trigger_steps)>0:
            operator = goal["operator"]

            goal_properties = Goal.get_properties(goal,level)

            for step in trigger_steps:
                if step["condition_type"] == "percentage" and step["condition_percentage"]:
                    current_percentage = float(value - previous_goal) / float(current_goal - previous_goal)
                    required_percentage = step["condition_percentage"]
                    if current_percentage>=1.0 and required_percentage!=1.0 and not step["execute_when_complete"]:
                        # When the user reaches the full goal, and there is a trigger at e.g. 90%, we don't want it to be executed anymore.
                        continue
                    if (operator == "geq" and current_percentage >= required_percentage) \
                        or (operator == "leq" and current_percentage <= required_percentage):
                        if exec_queue.get(step["goal_trigger_id"],{"step" : -sys.maxsize})["step"] < step["step"]:
                            exec_queue[step["goal_trigger_id"]] = step

            for step in exec_queue.values():
                current_percentage = float(value - previous_goal) / float(current_goal - previous_goal)
                GoalTriggerStep.execute(
                    trigger_step = step,
                    user_id = user_id,
                    current_percentage = current_percentage,
                    value = value,
                    goal_goal = current_goal,
                    goal_level = level,
                    goal_properties = goal_properties,
                    achievement_date = achievement_date
                )


    @classmethod
    def get_goal_eval_cache(cls,goal_id,achievement_date,user_id):
        """lookup and return cache entry, else return None"""
        v = cache_goal_evaluation.get("%s_%s_%s" % (goal_id,achievement_date,user_id))
        if v:
            return v
        else:
            return None

    @classmethod
    def set_goal_eval_cache(cls,goal, achievement_date, user_id,value,achieved):
        """set cache entry after evaluation"""
        cache_query = t_goal_evaluation_cache.select().where(and_(t_goal_evaluation_cache.c.goal_id==goal["id"],
                                                                  t_goal_evaluation_cache.c.user_id==user_id,
                                                                  t_goal_evaluation_cache.c.achievement_date==achievement_date))
        cache = DBSession.execute(cache_query).fetchone()

        if not cache:
            q = t_goal_evaluation_cache.insert()\
                                       .values({"user_id":user_id,
                                                "goal_id":goal["id"],
                                                "value" : value,
                                                "achieved" : achieved,
                                                "achievement_date" : achievement_date})
            update_connection().execute(q)
        elif cache["value"]!=value or cache["achieved"]!=achieved:
            #update
            q = t_goal_evaluation_cache.update()\
                                       .where(and_(t_goal_evaluation_cache.c.goal_id==goal["id"],
                                                   t_goal_evaluation_cache.c.user_id==user_id,
                                                   t_goal_evaluation_cache.c.achievement_date == achievement_date))\
                                       .values({"value" : value,
                                                "achieved" : achieved,
                                                "achievement_date": achievement_date})
            update_connection().execute(q)

        data = {
            "id" : goal["id"],
            "value" : value,
            "achieved" : achieved,
            "name_translation_id" : goal["name_translation_id"],
            "goal" : goal["goal"],
            "achievement_id" : goal["achievement_id"],
            "priority" : goal["priority"]
        }

        achievement_id = goal["achievement_id"]
        achievement = Achievement.get_achievement(achievement_id)

        level = min((Achievement.get_level_int(user_id, achievement["id"], achievement_date) or 0)+1,achievement["maxlevel"])

        goal_output = Goal.basic_goal_output(data,level)

        goal_output.update({
            "achieved" : achieved,
            "value" : value,
        })

        cache_goal_evaluation.set("%s_%s_%s" % (goal["id"],achievement_date,user_id),goal_output)

        return goal_output

    @classmethod
    def clear_goal_caches(cls, user_id, goal_ids_with_achievement_date):
        """clear the evaluation cache for the user and gaols"""
        for goal_id, achievement_date in goal_ids_with_achievement_date:
            cache_goal_evaluation.delete("%s_%s_%s" % (goal_id, achievement_date, user_id))
            s = update_connection()
            s.execute(t_goal_evaluation_cache.delete().where(
                and_(t_goal_evaluation_cache.c.user_id == user_id,
                     t_goal_evaluation_cache.c.goal_id == goal_id,
                     t_goal_evaluation_cache.c.achievement_date == achievement_date ))
            )

    @classmethod
    def get_leaderboard(cls, goal, achievement_date, user_ids):
        """get the leaderboard for the goal and userids"""

        q = select([t_goal_evaluation_cache.c.user_id,
                    t_goal_evaluation_cache.c.value])\
                .where(and_(t_goal_evaluation_cache.c.user_id.in_(user_ids),
                            t_goal_evaluation_cache.c.goal_id==goal["id"],
                            t_goal_evaluation_cache.c.achievement_date==achievement_date,
                            ))\
                .order_by(t_goal_evaluation_cache.c.value.desc(),
                          t_goal_evaluation_cache.c.user_id.desc())
        items = DBSession.execute(q).fetchall()

        users = User.get_users(user_ids)

        requested_user_ids = set(int(s) for s in user_ids)
        values_found_for_user_ids = set([int(x["user_id"]) for x in items])
        missing_user_ids = requested_user_ids - values_found_for_user_ids
        missing_users = User.get_users(missing_user_ids).values()
        if len(missing_users)>0:
            #the goal has not been evaluated for some users...
            achievement = Achievement.get_achievement(goal["achievement_id"])

            for user in missing_users:
                user_has_level = Achievement.get_level_int(user["id"], achievement["id"], achievement_date)
                user_wants_level = min((user_has_level or 0)+1, achievement["maxlevel"])

                Goal.evaluate(goal, achievement, achievement_date, user, user_wants_level)

            #rerun the query
            items = DBSession.execute(q).fetchall()

        positions = [{ "user": User.basic_output(users[items[i]["user_id"]]),
                       "value" : items[i]["value"],
                       "position" : i} for i in range(0,len(items))]

        return positions

    @classmethod
    @cache_general.cache_on_arguments()
    def get_goal_properties(cls,goal_id,level):
        """return all properties which are associated to the achievement level."""

        #NOT CACHED, as full-basic_output is cached (see Goal.basic_output)

        return DBSession.execute(select([t_goalproperties.c.id.label("property_id"),
                                         t_goalproperties.c.name,
                                         t_goalproperties.c.is_variable,
                                         t_goals_goalproperties.c.from_level,
                                         t_goals_goalproperties.c.value,
                                         t_goals_goalproperties.c.value_translation_id],
                                        from_obj=t_goalproperties.join(t_goals_goalproperties))\
                                 .where(and_(or_(t_goals_goalproperties.c.from_level<=level,
                                                 t_goals_goalproperties.c.from_level==None),
                                             t_goals_goalproperties.c.goal_id==goal_id))\
                                 .order_by(t_goals_goalproperties.c.from_level))\
                        .fetchall()

    @classmethod
    @cache_general.cache_on_arguments()
    def basic_goal_output(cls,goal,level):
        goal_goal = evaluate_value_expression(goal["goal"], {"level":level})
        properties = {
            str(r["property_id"]) : {
                "property_id" : r["property_id"],
                "name" : r["name"],
                "value" : evaluate_string(r["value"], {"level":level}),
                "value_translated" : Translation.trs(r["value_translation_id"], {"level":level}),
            } for r in Goal.get_goal_properties(goal["id"],level)
        }
        return {
            "goal_id" : goal["id"],
            "goal_name" : Translation.trs(goal["name_translation_id"], {"level":level, "goal":goal_goal}),
            "goal_goal" : goal_goal,
            "priority"  : goal["priority"],
            "properties" : properties,
            #"updated_at" : goal["updated_at"]
        }

    @classmethod
    @cache_general.cache_on_arguments()
    def get_properties(cls, goal, level):
        return {
            p["name"]: (p["value_translated"] if p["value_translated"] else p["value"])
            for p in Goal.basic_goal_output(goal, level).get("properties").values()
        }

class Language(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.name,)

class TranslationVariable(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.name,)

class Translation(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.text,)

    @classmethod
    @cache_translations.cache_on_arguments()
    def trs(cls,translation_id,params={}):
        """returns a map of translations for the translation_id for ALL languages"""

        if translation_id is None:
            return None
        try:
            # TODO support params which are results of this function itself (dicts of lang -> value)
            # maybe even better: add possibility to refer to other translationvariables directly (so they can be modified later on)
            ret = {str(x["name"]) : evaluate_string(x["text"],params) for x in cls.get_translation_variable(translation_id)}
        except Exception as e:
            ret = {str(x["name"]) : x["text"] for x in cls.get_translation_variable(translation_id)}
            log.exception("Evaluation of string-forumlar failed: %s" % (ret.get(get_settings().get("fallback_language","en"),translation_id),))
            
        if not get_settings().get("fallback_language","en") in ret:
            ret[get_settings().get("fallback_language","en")] = "[not_translated]_"+str(translation_id)
        
        for lang in cls.get_languages():
            if not str(lang["name"]) in ret:
                ret[str(lang["name"])] = ret[get_settings().get("fallback_language","en")]
        
        return ret    
    
    @classmethod
    @cache_translations.cache_on_arguments()
    def get_translation_variable(cls,translation_id):
        return DBSession.execute(select([t_translations.c.text,
                                  t_languages.c.name],
                              from_obj=t_translationvariables.join(t_translations).join(t_languages))\
                       .where(t_translationvariables.c.id==translation_id)).fetchall()
    
    @classmethod
    @cache_translations.cache_on_arguments()                   
    def get_languages(cls):
        return DBSession.execute(t_languages.select()).fetchall()

class UserMessage(ABase):
    def __unicode__(self, *args, **kwargs):
        return "Message: %s" % (Translation.trs(self.translation_id,self.params).get(get_settings().get("fallback_language","en")),)

    @classmethod
    def get_text(cls, row):
        return Translation.trs(row["translation_id"],row["params"])

    @property
    def text(self):
        return Translation.trs(self.translation_id, self.params)

    @classmethod
    def deliver(cls, message):
        from gengine.app.push import send_push_message
        text = UserMessage.get_text(message)
        language = get_settings().get("fallback_language", "en")
        j = t_users.join(t_languages)
        user_language = DBSession.execute(select([t_languages.c.name],from_obj=j).where(t_users.c.id==message["user_id"])).fetchone()
        if user_language:
             language = user_language["name"]
        translated_text = text[language]

        if not message["has_been_pushed"]:
            try:
                send_push_message(
                    user_id = message["user_id"],
                    text = translated_text,
                    custom_payload = {},
                    title = get_settings().get("push_title","Gamification-Engine")
                )
            except Exception as e:
                log.error(e, exc_info=True)
            else:
                DBSession.execute(t_user_messages.update().values({ "has_been_pushed" : True }).where(t_user_messages.c.id == message["id"]))

class GoalTrigger(ABase):
    def __unicode__(self, *args, **kwargs):
        return "GoalTrigger: %s" % (self.id,)

class GoalTriggerStep(ABase):
    def __unicode__(self, *args, **kwargs):
        return "GoalTriggerStep: %s" % (self.id,)

    @classmethod
    def execute(cls, trigger_step, user_id, current_percentage, value, goal_goal, goal_level, goal_properties, achievement_date, suppress_actions=False):
        uS = update_connection()
        uS.execute(t_goal_trigger_step_executions.insert().values({
            'user_id': user_id,
            'trigger_step_id': trigger_step["id"],
            'execution_level': goal_level,
            'achievement_date': achievement_date
        }))
        if not suppress_actions:
            if trigger_step["action_type"] == "user_message":
                m = UserMessage(
                    user_id = user_id,
                    translation_id = trigger_step["action_translation_id"],
                    params = dict({
                        'value' : value,
                        'goal' : goal_goal,
                        'percentage' : current_percentage
                    },**goal_properties),
                    is_read = False,
                    has_been_pushed = False
                )
                uS.add(m)

@event.listens_for(GoalTriggerStep, "after_insert")
@event.listens_for(GoalTriggerStep, 'after_update')
def insert_trigger_step_executions_after_step_upsert(mapper,connection,target):
    """When we create a new Trigger-Step, we must ensure, that is will not be executed for the users who already met the conditions before."""

    user_ids = [x["id"] for x in DBSession.execute(select([t_users.c.id,],from_obj=t_users)).fetchall()]
    users = User.get_users(user_ids).values()
    goal = target.trigger.goal
    achievement = goal.achievement

    for user in users:
        achievement_date = Achievement.get_datetime_for_evaluation_type(evaluation_timezone=achievement["evaluation_timezone"], evaluation_type=achievement["evaluation"])
        user_has_level = Achievement.get_level_int(user["id"], achievement["id"], achievement_date)
        user_wants_level = min((user_has_level or 0) + 1, achievement["maxlevel"])
        goal_eval = Goal.evaluate(goal, achievement, achievement_date, user, user_wants_level, None, execute_triggers=False)

        previous_goal = Goal.basic_goal_output(goal, user_wants_level - 1).get("goal_goal", 0)
        if previous_goal == goal_eval["goal_goal"]:
            previous_goal = 0.0

        current_percentage = float(goal_eval["value"]-previous_goal) / float(goal_eval["goal_goal"]-previous_goal)
        operator = goal["operator"]
        required_percentage = target["condition_percentage"]

        if (operator == "geq" and current_percentage >= required_percentage) \
                or (operator == "leq" and current_percentage <= required_percentage):
            GoalTriggerStep.execute(
                trigger_step=target,
                user_id=user["id"],
                current_percentage=current_percentage,
                value=goal_eval["value"],
                goal_goal=goal_eval["goal_goal"],
                goal_level=user_wants_level,
                goal_properties=Goal.get_properties(goal,user_wants_level),
                achievement_date=achievement_date,
                suppress_actions = True
            )

def backref(*args,**kw):
    if not "passive_deletes" in kw:
        kw["passive_deletes"] = True
    return sa_backref(*args,**kw)

def relationship(*args,**kw):
    if not "passive_deletes" in kw:
        kw["passive_deletes"] = True
    if "backref" in kw:
        if type(kw["backref"]=="str"):
            kw["backref"] = backref(kw["backref"])
    return sa_relationship(*args,**kw)

mapper(AuthUser, t_auth_users, properties={
    'roles' : relationship(AuthRole, secondary=t_auth_users_roles, backref="users")
})

mapper(AuthToken, t_auth_tokens, properties={
    'user' : relationship(AuthUser, backref="tokens")
})

mapper(AuthRole, t_auth_roles, properties={

})

mapper(AuthRolePermission, t_auth_roles_permissions, properties={
    'role' : relationship(AuthRole, backref="permissions"),
})

mapper(User, t_users, properties={
    'friends': relationship(User, secondary=t_users_users, 
                                 primaryjoin=t_users.c.id==t_users_users.c.from_id,
                                 secondaryjoin=t_users.c.id==t_users_users.c.to_id),
    'language' : relationship(Language,backref="users"),
})

mapper(UserDevice, t_user_device, properties={
    'user' : relationship(User, backref="devices"),
})

mapper(Group, t_groups, properties={
    'users' : relationship(User, secondary=t_users_groups, backref="groups"),
})

mapper(Variable, t_variables, properties={
   'values' : relationship(Value),
})
mapper(Value, t_values,properties={
   'user' : relationship(User),
   'variable' : relationship(Variable)
})
mapper(AchievementCategory, t_achievementcategories)
mapper(Achievement, t_achievements, properties={
   'requirements': relationship(Achievement, secondary=t_requirements, 
                                primaryjoin=t_achievements.c.id==t_requirements.c.from_id,
                                secondaryjoin=t_achievements.c.id==t_requirements.c.to_id,
                                ),
   'denials': relationship(Achievement, secondary=t_denials,
                           primaryjoin=t_achievements.c.id==t_denials.c.from_id,
                           secondaryjoin=t_achievements.c.id==t_denials.c.to_id,
                           ),
   'users': relationship(AchievementUser, backref='achievement'),
   'properties' : relationship(AchievementAchievementProperty, backref='achievement'),
   'rewards' : relationship(AchievementReward, backref='achievement'),
   'goals': relationship(Goal, backref='achievement'),
   'achievementcategory' : relationship(AchievementCategory, backref='achievements')
})
mapper(AchievementProperty, t_achievementproperties)
mapper(AchievementAchievementProperty, t_achievements_achievementproperties, properties={
   'property' : relationship(AchievementProperty, backref='achievements'),
   'value_translation' : relationship(TranslationVariable)
})
mapper(Reward, t_rewards)
mapper(AchievementReward, t_achievements_rewards, properties={
   'reward' : relationship(Reward, backref='achievements'),
   'value_translation' : relationship(TranslationVariable)
})
mapper(AchievementUser, t_achievements_users)

mapper(Goal, t_goals, properties={
    'name_translation' : relationship(TranslationVariable),
})
mapper(GoalProperty, t_goalproperties)
mapper(GoalGoalProperty, t_goals_goalproperties, properties={
   'property' : relationship(GoalProperty, backref='goals'),
   'value_translation' : relationship(TranslationVariable),
   'goal' : relationship(Goal, backref='properties',),
})
mapper(GoalEvaluationCache, t_goal_evaluation_cache,properties={
   'user' : relationship(User),
   'goal' : relationship(Goal)
})

mapper(GoalTrigger,t_goal_triggers, properties={
    'goal' : relationship(Goal,backref="triggers"),
})
mapper(GoalTriggerStep,t_goal_trigger_steps, properties={
    'trigger' : relationship(GoalTrigger,backref="steps"),
    'action_translation' : relationship(TranslationVariable)
})

mapper(Language, t_languages)
mapper(TranslationVariable,t_translationvariables)
mapper(Translation, t_translations, properties={
   'language' : relationship(Language),
   'translationvariable' : relationship(TranslationVariable, backref="translations"),
})

mapper(UserMessage, t_user_messages, properties = {
    'user' : relationship(User, backref="user_messages"),
    'translationvariable' : relationship(TranslationVariable),
})

@event.listens_for(AchievementProperty, "after_insert")
@event.listens_for(AchievementProperty, 'after_update')
def insert_variable_for_property(mapper,connection,target):
    """when setting is_variable on a :class:`AchievementProperty` a variable is automatically created"""
    if target.is_variable and not exists_by_expr(t_variables, t_variables.c.name==target.name):
            variable = Variable()
            variable.name = target.name
            variable.group = "day"
            DBSession.add(variable)
