# -*- coding: utf-8 -*-
"""models including business logic"""

import pytz
import datetime
import sqlalchemy.types as ty
from pyramid_dogpile_cache import get_region

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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    mapper,
    relationship
)

from sqlalchemy.dialects.postgresql import TIMESTAMP
from pytz.exceptions import UnknownTimeZoneError
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import sessionmaker, Session
from zope.sqlalchemy.datamanager import ZopeTransactionExtension, mark_changed
from datetime import timedelta
from gengine import urlcache
import transaction
from _collections import defaultdict
from pytz import timezone
import hashlib
import warnings

from gengine.metadata import Base, DBSession
import __builtin__

try:
    cache_general = get_region('general')
    cache_achievement_eval = get_region('achievement_eval')
    cache_achievements_by_user_for_today = get_region('achievements_by_user_for_today')
    cache_translations = get_region('translations')
except:
    from dogpile.cache import make_region

    cache_general = make_region().configure('dogpile.cache.memory')
    cache_achievement_eval = make_region().configure('dogpile.cache.memory')
    cache_achievements_by_user_for_today = make_region().configure('dogpile.cache.memory')
    cache_translations = make_region().configure('dogpile.cache.memory')
    
    warnings.warn("Warning: cache objects are in memory, are you creating docs?")

t_users = Table("users", Base.metadata,
    Column('id', ty.BigInteger, primary_key = True),
    Column("lat", ty.Float(Precision=64), nullable=True),
    Column("lng", ty.Float(Precision=64), nullable=True),
    Column("timezone", ty.String(), nullable=False, default="UTC"),
    Column("country", ty.String(), nullable=True, default=None),
    Column("region", ty.String(), nullable=True, default=None),
    Column("city", ty.String(), nullable=True, default=None),
    Column('created_at', ty.DateTime, nullable = False, default=datetime.datetime.utcnow),
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
    Column('relevance',ty.Enum("friends","city","own", name="relevance_types"), default="own"),
)

t_goals = Table("goals", Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False, default=""), #internal use
    Column('name_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable = True),
    #TODO: deprecate name_translation
    Column('condition', ty.String(255), nullable=True),
    Column('evaluation',ty.Enum("immediately","daily","weekly","monthly","yearly","end", name="evaluation_types")),
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
    Column("goal_id", ty.Integer, ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("user_id", ty.BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column("achieved", ty.Boolean),
    Column("value", ty.Float),
)

t_variables = Table('variables', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False, index=True),
    Column('group', ty.Enum("year","month","week","day","timeslot","none", name="variable_group_types"), nullable = False, default="none"),
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
    Column('user_id', ty.BigInteger, ForeignKey("users.id"), primary_key = True, index=True, nullable=False),
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('level', ty.Integer, primary_key = True, default=1),
    Column('updated_at', ty.DateTime, nullable = False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow),
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
   Column('name', ty.String(255), nullable = False),
)

t_translationvariables = Table('translationvariables', Base.metadata,
   Column('id', ty.Integer, primary_key = True),
   Column('name', ty.String(255), nullable = False),
)

t_translations = Table('translations', Base.metadata,
   Column('id', ty.Integer, primary_key = True),
   Column('translationvariable_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="CASCADE"), nullable = False),
   Column('language_id', ty.Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable = False),
   Column('text', ty.Text(), nullable = False),
)

class ABase(object):
    """abstract base class which introduces a nice constructor for the model classes."""
    
    def __init__(self,*args,**kw):
        """ create a model object.
        
        pass attributes by using named parameters, e.g. name="foo", value=123
        """
        
        for k,v in kw.items():
            setattr(self, k, v)
            
    def __str__(self):
        if hasattr(self, "__unicode__"):
            return self.__unicode__()

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
    def get_cache_expiration_time_for_today(cls,user):
        """return the seconds until the day of the user ends (timezone of the user).
        
        This is needed as achievements may be limited to a specific time (e.g. only during holidays)."""
        
        tzobj = pytz.timezone(user["timezone"])
        now = datetime.datetime.now(tzobj)
        today = now.replace(hour=0,minute=0,second=0,microsecond=0)
        tomorrow = today+timedelta(days=1)
        return int((tomorrow-today).total_seconds())

    @classmethod
    def set_infos(cls,user_id,lat,lng,timezone,country,region,city,friends, groups):
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
        
class Group(ABase):
    def __unicode__(self, *args, **kwargs):
        return "(ID: %s)" % (self.id,)

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
    def get_datetime_for_tz_and_group(cls,tz,group):
        """get the datetime of the current row, needed for grouping
        
        when "timezone" is used as a group name, the values are grouped to the nearest time in (09:00, 12:00, 15:00, 18:00, 21:00)
        (timezone to use is given as parameter)
        """
        tzobj = pytz.timezone(tz)
        now = datetime.datetime.now(tzobj)
        #now = now.replace(tzinfo=pytz.utc)
        
        t = None
        if group=="year":
            t = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0 )
        elif group=="month":
            t = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif group=="week":
            t = now-datetime.timedelta(days=now.weekday())
            t = t.replace(hour=0, minute=0, second=0, microsecond=0)
        elif group=="day":
            t = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif group=="timeslot":
            
            tslist = [
                (now-datetime.timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0),
                now.replace(hour=9, minute=0, second=0, microsecond=0),
                now.replace(hour=12, minute=0, second=0, microsecond=0),
                now.replace(hour=15, minute=0, second=0, microsecond=0),
                now.replace(hour=18, minute=0, second=0, microsecond=0),
                now.replace(hour=21, minute=0, second=0, microsecond=0),
                (now+datetime.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0),
            ]
            
            t = min(tslist,key=lambda date : abs(dt-date))
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
            if not m.has_key(row["variable_id"]):
                m[row["variable_id"]] = []
            
            m[row["variable_id"]].append({"goal":row,"achievement":Achievement.get_achievement(row["achievement_id"])})
            
        return m
    
    @classmethod
    def invalidate_caches_for_variable_and_user(cls,variable_id,user_id):
        """ invalidate the relevant caches for this user and all relevant users with concerned leaderboards"""
        goalsandachievements = cls.map_variables_to_rules().get(variable_id,[])

        Goal.clear_goal_caches(user_id, [entry["goal"]["id"] for entry in goalsandachievements])
        for entry in goalsandachievements:
            Achievement.invalidate_evaluate_cache(user_id,entry["achievement"])
             
    
class Value(ABase):
    """A Value describes the relation of the user to a variable.
    
    (e.g. it counts the occurences of the "events" which the variable represents) """
    
    @classmethod
    def increase_value(cls, variable_name, user, value, key):
        """increase the value of the variable for the user.
        
        In addition to the variable_name there may be an application-specific key which can be used in your :class:`.Goal` definitions
        """
        
        user_id = user["id"]
        tz = user["timezone"]
        
        variable = Variable.get_variable_by_name(variable_name)
        datetime = Variable.get_datetime_for_tz_and_group(tz,variable["group"])
        
        condition = and_(t_values.c.datetime==datetime,
                         t_values.c.variable_id==variable["id"],
                         t_values.c.user_id==user_id,
                         t_values.c.key==str(key))
        
        current_value = DBSession.execute(select([t_values.c.value,]).where(condition)).scalar()
        
        if current_value is not None:
            update_connection().execute(t_values.update(condition, values={"value":current_value+value}))
        else:
            update_connection().execute(t_values.insert({"datetime":datetime,
                                           "variable_id":variable["id"],
                                           "user_id" : user_id,
                                           "key" : str(key),
                                           "value":value}))

        Variable.invalidate_caches_for_variable_and_user(variable["id"],user["id"])
        
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
            
            return [update(arr,by_loc[arr["id"]]) for arr in by_date if by_loc.has_key(arr["id"])]
        
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
        return [dict(x.items()) for x in DBSession.execute(q).fetchall() if len(Goal.get_goals(x['id']))>0]
    
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
        
        dependes on the "relevance" attribute of the achivement, can be "friends" or "city" (city is still a todo)
        """
        # this is needed to compute the leaderboards
        users=[user_id,] 
        if achievement["relevance"]=="city":
            #TODO
            pass
        elif achievement["relevance"]=="friends":
            users += [x["to_id"] for x in DBSession.execute(select([t_users_users.c.to_id,], t_users_users.c.from_id==user_id)).fetchall()]
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
        return set(users)
    
    #TODO:CACHE
    @classmethod
    def get_level(cls, user_id, achievement_id):
        """get the current level of the user for this achievement."""
        
        q = select([t_achievements_users.c.level,
                    t_achievements_users.c.updated_at],
                       and_(t_achievements_users.c.user_id==user_id,
                            t_achievements_users.c.achievement_id==achievement_id)).order_by(t_achievements_users.c.level.desc())
        return DBSession.execute(q).fetchall()
    
    @classmethod
    def get_level_int(cls,user_id,achievement_id):
        """get the current level of the user for this achievement as int (0 if the user does not have this achievement)"""
        lvls = Achievement.get_level(user_id, achievement_id)
        
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
                        "value" : eval_formular(r["value"], {"level":i}),
                        "value_translated" : Translation.trs(r["value_translation_id"], {"level":i}),
                    } for r in Achievement.get_rewards(achievement["id"],i)},
                    "properties" : {str(r["property_id"]) : {
                        "property_id" : r["property_id"],
                        "name" : r["name"],
                        "value" : eval_formular(r["value"], {"level":i}),
                        "value_translated" : Translation.trs(r["value_translation_id"], {"level":i}),
                    } for r in Achievement.get_achievement_properties(achievement["id"],i)}
            } for i in range(0,max_level_included+1)}
        return out
    
    @classmethod
    def evaluate(cls, user, achievement_id):
        """evaluate the achievement including all its subgoals for the user.
        
           return the basic_output for the achievement plus information about the new achieved levels
        """
        
        def generate():
            user_id = user["id"]
            achievement = Achievement.get_achievement(achievement_id)
            user_ids = Achievement.get_relevant_users_by_achievement_and_user(achievement, user_id)
            
            user_has_level = Achievement.get_level_int(user_id, achievement["id"])
            user_wants_level = min((user_has_level or 0)+1, achievement["maxlevel"])
            
            goal_evals={}
            all_goals_achieved = True
            goals = Goal.get_goals(achievement["id"])
            
            for goal in goals:
    
                goal_eval = Goal.get_goal_eval_cache(goal["id"], user_id)
                if not goal_eval:
                    Goal.evaluate(goal, [user_id,], user_wants_level)
                    goal_eval = Goal.get_goal_eval_cache(goal["id"], user_id)
                    
                if achievement["relevance"]=="friends" or achievement["relevance"]=="city":
                    goal_eval["leaderboard"] = Goal.get_leaderboard(goal, user_ids)
                    goal_eval["leaderboard_position"] = filter(lambda x : x["user_id"]==user_id, goal_eval["leaderboard"])[0]["position"]
                
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
                            "value" : eval_formular(r["value"], {"level":user_wants_level}),
                            "value_translated" : Translation.trs(r["value_translation_id"], {"level":user_wants_level}),
                        } for r in Achievement.get_rewards(achievement["id"],user_wants_level)
                     },
                    "properties" : {
                        str(r["property_id"]) : {
                            "property_id" : r["property_id"],
                            "name" : r["name"],
                            "is_variable" : r["is_variable"],
                            "value" : eval_formular(r["value"], {"level":user_wants_level}),
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
                    "level" : user_wants_level
                }))
                
                user_has_level = user_wants_level
                user_wants_level = user_wants_level+1
                    
                Goal.clear_goal_caches(user_id, [g["goal_id"] for g in goal_evals.values()])
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
                        str(x["level"]) : x["updated_at"] for x in Achievement.get_level(user_id, achievement["id"])
                    },
                   "maxlevel" : achievement["maxlevel"],
                   "new_levels" : {},
                   "goals":goal_evals,
                   #"updated_at":combine_updated_at([achievement["updated_at"],] + [g["updated_at"] for g in goal_evals])
                })
            
            if new_level_output is not None: #if we reached a new level in this recursion step, add the previous levels rewards and properties
                output["new_levels"][str(user_has_level)]=new_level_output
                
            return output
        
        return cache_achievement_eval.get_or_create("%s_%s" % (user["id"],achievement_id),generate)
    
    @classmethod
    def invalidate_evaluate_cache(cls,user_id,achievement):
        """invalidate the evaluation cache for all goals of this achievement for the user."""
        
        #We neeed to invalidate for all relevant users because of the leaderboards
        for uid in Achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user_id):
            cache_achievement_eval.delete("%s_%s" % (uid,achievement["id"]))
            urlcache.invalidate("/progress/"+str(uid))
    
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
        build_hash = lambda x,l : hashlib.md5(str(x["id"])+str(eval_formular(x["value"], {"level":l}))+str(Translation.trs(x["value_translation_id"], {"level":l}))).hexdigest() 
        
        prev_hashes = {build_hash(x,level-1) for x in prev_level}
        this_hashes = {build_hash(x,level) for x in this_level}
        
        retlist = [x for x in this_level if not build_hash(x,level) in prev_hashes]
        return retlist
    
    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievement_properties(cls,achievement_id,level):
        """return all properties which are associated to the achievement level."""
        
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
        if self.name_translation!=None:
            name = Translation.trs(self.name_translation.id, {"level":1, "goal":'0'})[_fallback_language]
            return str(name) + " (ID: %s)" % (self.id,)
        else:
            return self.name + " (ID: %s)" % (self.id,)
    
    @classmethod
    @cache_general.cache_on_arguments()
    def get_goals(cls,achievement_id):
        return DBSession.execute(t_goals.select(t_goals.c.achievement_id==achievement_id)).fetchall()
    
    @classmethod
    def compute_progress(cls,goal,user_ids):
        """computes the progress of the goal for the given user_ids
        
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
        condition = eval_formular(goal["condition"],{"var" : t_variables.c.name.label("variable_name"),
                                                     "key" : t_values.c.key})
        group_by_dateformat = goal["group_by_dateformat"]
        group_by_key = goal["group_by_key"]
        timespan = goal["timespan"]
        maxmin = goal["maxmin"]
        evaluation_type = goal["evaluation"]
        
        #prepare
        select_cols=[func.sum(t_values.c.value).label("sum"),
                     t_values.c.user_id]
         
        j = t_values.join(t_variables)\
                    .join(t_users)
         
        datetime_col=None
        if group_by_dateformat:
            # here we need to convert to users' time zone, as we might need to group by e.g. USER's weekday
            datetime_col = func.to_char(text("values.datetime AT TIME ZONE users.timezone"),group_by_dateformat).label("datetime")
            select_cols.append(datetime_col)
            
        if group_by_key:
            select_cols.append(t_values.c.key)

        #build query
        q = select(select_cols,
                   from_obj=j)\
           .where(t_values.c.user_id.in_(user_ids))\
           .group_by(t_values.c.user_id)
         
        if condition is not None:
            q = q.where(condition)
            
        if timespan:
            #here we can use the utc time
            q = q.where(t_values.c.datetime>=datetime.datetime.utcnow()-datetime.timedelta(days=timespan))
        
        if evaluation_type!="immediately":

            if evaluation_type=="daily":
                q = q.where(text("values.datetime AT TIME ZONE users.timezone>"+datetime_trunc("day","users.timezone")))
            elif evaluation_type=="weekly":
                q = q.where(text("values.datetime AT TIME ZONE users.timezone>"+datetime_trunc("week","users.timezone")))
            elif evaluation_type=="monthly":
                q = q.where(text("values.datetime AT TIME ZONE users.timezone>"+datetime_trunc("month","users.timezone")))
            elif evaluation_type=="yearly":
                q = q.where(text("values.datetime AT TIME ZONE users.timezone>"+datetime_trunc("year","users.timezone")))
         
        if datetime_col:
            q = q.group_by(datetime_col)
     
        if group_by_key:
            q = q.group_by(t_values.c.key)
     
        query_with_groups = q.alias()
     
        select_cols2 = [query_with_groups.c.user_id]
        
        if maxmin=="min":
            select_cols2.append(func.min(query_with_groups.c.sum).label("value"))
        else:
            select_cols2.append(func.max(query_with_groups.c.sum).label("value"))
     
        combined_user_query = select(select_cols2,from_obj=query_with_groups)\
                              .group_by(query_with_groups.c.user_id)
        
        return DBSession.execute(combined_user_query).fetchall()

    @classmethod
    def evaluate(cls, goal, user_ids, level):
        """evaluate the goal for the user_ids and the level"""
        
        operator = goal["operator"]
        
        users_progress = Goal.compute_progress(goal,user_ids)
        
        goal_evaluation = {e["user_id"] : e["value"] for e in users_progress}
        
        for user_id in user_ids:
            goal_achieved = False

            before = cls.get_goal_eval_cache(goal["id"], user_id)
            new = goal_evaluation.get(user_id,0.0)
            
            if before is None or before.get("value",0.0)!=goal_evaluation.get(user_id,0.0):
                
                #Level is the next level, or the current level if I'm alread at max
                params = {
                    "level" : level
                }

                goal_goal = eval_formular(goal["goal"], params)
    
                if goal_goal is not None and operator=="geq" and new>=goal_goal:
                    goal_achieved = True
                    new = min(new,goal_goal)
                        
                elif goal_goal is not None and operator=="leq" and new<=goal_goal:
                    goal_achieved = True
                    new = max(new,goal_goal)
                
                Goal.set_goal_eval_cache(goal_id=goal["id"],
                                                user_id=user_id,
                                                value=new,
                                                achieved = goal_achieved)
            
    @classmethod
    def get_goal_eval_cache(cls,goal_id,user_id):
        """lookup and return cache entry, else return None"""
        j = t_goal_evaluation_cache.join(t_goals)
        q = select([t_goal_evaluation_cache.c.goal_id.label("id"),
                    t_goal_evaluation_cache.c.value,
                    t_goal_evaluation_cache.c.achieved,
                    #t_goal_evaluation_cache.c.updated_at,
                    t_goals.c.name_translation_id,
                    t_goals.c.goal,
                    t_goals.c.achievement_id,
                    t_goals.c.priority],
                   and_(t_goal_evaluation_cache.c.goal_id==goal_id,
                        t_goal_evaluation_cache.c.user_id==user_id),
                   from_obj=j)
        
        cache = DBSession.execute(q).fetchone()
        
        if cache:
            achievement_id = cache["achievement_id"]
            achievement = Achievement.get_achievement(achievement_id)
            
            level = min((Achievement.get_level_int(user_id, achievement["id"]) or 0)+1,achievement["maxlevel"])
            
            goal_output = Goal.basic_goal_output(cache,level)
            
            goal_output.update({
                "achieved" : cache["achieved"],
                "value" : cache["value"],
            })
            
            return goal_output
        else:
            return None
        
    @classmethod
    def set_goal_eval_cache(cls,goal_id,user_id,value,achieved):
        """set cache entry after evaluation"""
        
        cache = Goal.get_goal_eval_cache(goal_id, user_id)
        
        if not cache:
            q = t_goal_evaluation_cache.insert()\
                                       .values({"user_id":user_id,
                                                "goal_id":goal_id,
                                                "value" : value,
                                                "achieved" : achieved})
            update_connection().execute(q)
        elif cache["value"]!=value or cache["achieved"]!=achieved:
            #update
            q = t_goal_evaluation_cache.update()\
                                       .where(and_(t_goal_evaluation_cache.c.goal_id==goal_id,
                                                   t_goal_evaluation_cache.c.user_id==user_id))\
                                       .values({"value" : value,
                                                "achieved" : achieved})
            update_connection().execute(q)
    
    @classmethod
    def clear_goal_caches(cls, user_id, goal_ids):
        """clear the evaluation cache for the user and gaols"""
        
        update_connection().execute(t_goal_evaluation_cache.delete().where(and_(t_goal_evaluation_cache.c.user_id==user_id,
                                                                      t_goal_evaluation_cache.c.goal_id.in_(goal_ids))))
    @classmethod
    def get_leaderboard(cls, goal, user_ids):
        """get the leaderboard for the goal and userids"""
        q = select([t_goal_evaluation_cache.c.user_id,
                    t_goal_evaluation_cache.c.value])\
                .where(and_(t_goal_evaluation_cache.c.user_id.in_(user_ids),
                            t_goal_evaluation_cache.c.goal_id==goal["id"]))\
                .order_by(t_goal_evaluation_cache.c.value.desc(),
                          t_goal_evaluation_cache.c.user_id.desc())
        items = DBSession.execute(q).fetchall()
        
        missing_users = set(user_ids)-set([x["user_id"] for x in items])
        if len(missing_users)>0:
            #the goal has not been evaluated for some users...
            achievement = Achievement.get_achievement(goal["achievement_id"])
            
            for user_id in missing_users:
                user = User.get_user(user_id)
                
                user_has_level = Achievement.get_level_int(user_id, achievement["id"])
                user_wants_level = min((user_has_level or 0)+1, achievement["maxlevel"])
            
                Goal.evaluate(goal, [user_id,], user_wants_level)
                goal_eval = Goal.get_goal_eval_cache(goal["id"], user_id)
            
            #rerun the query
            items = DBSession.execute(q).fetchall()
            
        positions = [{ "user_id" : items[i]["user_id"],
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
        goal_goal = eval_formular(goal["goal"], {"level":level})
        properties = {
            str(r["property_id"]) : {
                "property_id" : r["property_id"],
                "name" : r["name"],
                "value" : eval_formular(r["value"], {"level":level}),
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
        

class Language(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.name,)

class TranslationVariable(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.name,)

_fallback_language="en"
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
            ret = {str(x["name"]) : eval_formular(x["text"],params) for x in cls.get_translation_variable(translation_id)}
        except:
            ret = {str(x["name"]) : x["text"] for x in cls.get_translation_variable(translation_id)}
            
        if not ret.has_key(_fallback_language):
            ret[_fallback_language] = "[not_translated]_"+str(translation_id) 
        
        for lang in cls.get_languages():
            if not ret.has_key(str(lang["name"])):
                ret[str(lang["name"])] = ret[_fallback_language]
        
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
            
mapper(User, t_users, properties={
    'friends': relationship(User, secondary=t_users_users, 
                                 primaryjoin=t_users.c.id==t_users_users.c.from_id,
                                 secondaryjoin=t_users.c.id==t_users_users.c.to_id)
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
    'properties' : relationship(GoalGoalProperty, backref='goal'),
})
mapper(GoalProperty, t_goalproperties)
mapper(GoalGoalProperty, t_goals_goalproperties, properties={
   'property' : relationship(GoalProperty, backref='goals'),
   'value_translation' : relationship(TranslationVariable)
})
mapper(GoalEvaluationCache, t_goal_evaluation_cache,properties={
   'user' : relationship(User),
   'goal' : relationship(Goal)
})

mapper(Language, t_languages)
mapper(TranslationVariable,t_translationvariables)
mapper(Translation, t_translations, properties={
   'language' : relationship(Language),
   'translationvariable' : relationship(TranslationVariable, backref="translations"),
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

#some query helpers
 
def calc_distance(latlong1, latlong2):
    """generates a sqlalchemy expression for distance query in miles
    
       :param latlong1: the location from which we look for rows, as tuple (lat,lng)
       
       :param latlong2: the columns containing the latitude and longitude, as tuple (lat,lng) 
    """
    
    #explain: http://geokoder.com/distances
    
    #return func.sqrt(func.pow(69.1 * (latlong1[0] - latlong2[0]),2)
    #               + func.pow(53.0 * (latlong1[1] - latlong2[1]),2))

    return func.sqrt(func.pow(111.2 * (latlong1[0]-latlong2[0]),2)
           + func.pow(111.2 * (latlong1[1]-latlong2[1]) * func.cos(latlong2[0]),2))
    
def coords(row):
    return (row["lat"],row["lng"])

safe_list = ['math','acos', 'asin', 'atan', 'atan2', 'ceil',
             'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor',
             'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 'modf',
             'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'sum', 'range', 'str', 'int', 'float']

#use the list to filter the local namespace
from math import *
safe_dict = dict([ (k, locals().get(k, None)) for k in safe_list])
for k in safe_dict.keys():
    if safe_dict[k] is None:
        if hasattr(__builtin__, k):
            safe_dict[k] = getattr(__builtin__, k)
safe_dict['and_'] = and_
safe_dict['or_'] = or_
safe_dict['abs'] = abs

class FormularEvaluationException(Exception):
    pass

#TODO: Cache
def eval_formular(s,params={}):
    """evaluates the formular.
    
    parameters are available as p.name,
    
    available math functions:
    'math','acos', 'asin', 'atan', 'atan2', 'ceil',
    'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor',
    'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 'modf',
    'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'sum', 'range'
    """
    try:
        if s is None:
            return None
        else:
            p = DictObjectProxy(params)
            
            #add any needed builtins back in.
            safe_dict['p'] = p
            
            result = eval(s,{"__builtins__":None},safe_dict)
            if type(result)==str or type(result)==unicode:
                return result % params
            else:
                return result
    except:
        raise FormularEvaluationException(s)
    
class DictObjectProxy():
    obj = None
    
    def __init__(self, obj):
        self.obj = obj
    def __getattr__(self, name):
        if not name in self.obj:
            return ""
        return self.obj[name]

def combine_updated_at(list_of_dates):
    return max(list_of_dates)

def get_insert_id_by_result(r):
    return r.last_inserted_ids()[0]

def get_insert_ids_by_result(r):
    return r.last_inserted_ids()

def exists_by_expr(t, expr):
    #TODO: use exists instead of count
    q = select([func.count("*").label("c")], from_obj=t).where(expr)
    r = DBSession.execute(q).fetchone()
    if r.c > 0:
        return True
    else:
        return False
    
@cache_general.cache_on_arguments()
def datetime_trunc(field,timezone):
    return "date_trunc('%(field)s', CAST(to_char(NOW() AT TIME ZONE %(timezone)s, 'YYYY-MM-DD HH24:MI:SS') AS TIMESTAMP)) AT TIME ZONE %(timezone)s" % {
                "field" : field,
                "timezone" : timezone
            }
    
@cache_general.cache_on_arguments()
def valid_timezone(timezone):
    try:
        pytz.timezone(timezone)
    except UnknownTimeZoneError:
        return False
    return True

def update_connection():
    session = DBSession()
    mark_changed(session)
    return session

def clear_all_caches():
    cache_achievement_eval.invalidate(hard=True)
    cache_achievements_by_user_for_today.invalidate(hard=True)
    cache_translations.invalidate(hard=True)
    cache_general.invalidate(hard=True)
    urlcache.invalidate_all()
