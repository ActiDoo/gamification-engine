# -*- coding: utf-8 -*-
"""models including business logic"""

import datetime
import logging
from datetime import timedelta

import hashlib
import pytz
import sqlalchemy.types as ty
from dateutil import relativedelta
from sqlalchemy.dialects.postgresql import JSON
import sys

from pyramid.settings import asbool
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.ddl import DDL
from sqlalchemy.sql.schema import UniqueConstraint, Index
from sqlalchemy.sql.sqltypes import Integer, String

from gengine.app.permissions import perm_global_increase_value
from gengine.base.model import ABase, exists_by_expr, calc_distance, coords, update_connection
from gengine.app.cache import cache_general, cache_goal_evaluation, cache_achievements_subjects_levels, \
    cache_achievements_by_subject_for_today, cache_translations
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
from gengine.base.util import dt_now, dt_ago, dt_in, normalize_key
from gengine.metadata import Base, DBSession

from gengine.app.formular import evaluate_condition, evaluate_value_expression, evaluate_string

log = logging.getLogger(__name__)


# Subjects are the actors and the organization of actors
# Which type of subjects do we have? (e.g. User, Team, City, Country,...)
t_subjecttypes = Table("subjecttypes", Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column("name", ty.String(100), unique=True, nullable=False),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# Defined the allowed hierarchy of subjects (users in teams and citys; cities in countries)
t_subjecttypes_subjecttypes = Table("subjecttypes_subjecttypes", Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('subjecttype_id', ty.Integer, ForeignKey("subjecttypes.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('part_of_id', ty.Integer, ForeignKey("subjecttypes.id", ondelete="CASCADE"), index=True, nullable=False),
    UniqueConstraint("subjecttype_id", "part_of_id")
)

# Check for Cycle!
t_subjecttypes_subjecttypes_ddl = DDL("""
    CREATE OR REPLACE FUNCTION check_subjecttypes_subjecttypes_cycle() RETURNS trigger AS $$
    DECLARE
        cycles INTEGER;
    BEGIN
        LOCK TABLE subjecttypes_subjecttypes IN ACCESS EXCLUSIVE MODE;
        WITH RECURSIVE search_graph(part_of_id, subjecttype_id, depth, path, cycle) AS (
                SELECT tt.part_of_id, t1.id, 1, ARRAY[t1.id], false FROM subjecttypes t1
                LEFT JOIN subjecttypes_subjecttypes AS tt ON tt.subjecttype_id=t1.id
            UNION ALL
                SELECT g.part_of_id, g.subjecttype_id, sg.depth + 1, path || g.subjecttype_id, g.subjecttype_id = ANY(path)
                FROM subjecttypes_subjecttypes g, search_graph sg
                WHERE g.part_of_id = sg.subjecttype_id AND NOT cycle
        )
        SELECT INTO cycles COUNT(*) FROM search_graph WHERE cycle=true;
        RAISE NOTICE 'cycles: %%', cycles;
        IF cycles > 0 THEN
           RAISE EXCEPTION 'cycle';
        END IF;
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER check_subjecttypes_subjecttypes_cycle AFTER INSERT OR UPDATE ON subjecttypes_subjecttypes
        FOR EACH ROW EXECUTE PROCEDURE check_subjecttypes_subjecttypes_cycle();
""")
event.listen(t_subjecttypes_subjecttypes, 'after_create', t_subjecttypes_subjecttypes_ddl.execute_if(dialect='postgresql'))

# Subjects are the actors and the organization of actors.
# These are the instances (e.g. users, cities, teams)
t_subjects = Table("subjects", Base.metadata,
   Column('id', ty.BigInteger, primary_key = True),
   Column('subjecttype_id', ty.Integer, ForeignKey("subjecttypes.id", ondelete="CASCADE"), nullable=False, index=True),
   Column("name", ty.String, index=True, nullable=True),

   Column("lat", ty.Float(Precision=64), nullable=True),
   Column("lng", ty.Float(Precision=64), nullable=True),

   Column("language_id", ty.Integer, ForeignKey("languages.id"), nullable=True),
   Column("timezone", ty.String(), nullable=False, default="UTC"),
   Column("additional_public_data", JSON(), nullable=True, default=None),

   Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# The relations of subjects (directed acyclic graph)
t_subjects_subjects = Table("subjects_subjects", Base.metadata,
    Column('id', ty.BigInteger, primary_key=True),
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('part_of_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('joined_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
    Column('left_at', TIMESTAMP(timezone=True), nullable=True, default=None, index=True),
    UniqueConstraint("subject_id", "part_of_id", "joined_at")
)

# Check for Cycle!
t_subjects_subjects_ddl = DDL("""
    CREATE OR REPLACE FUNCTION check_subjects_subjects_cycle() RETURNS trigger AS $$
    DECLARE
        cycles INTEGER;
    BEGIN
        LOCK TABLE subjects_subjects IN ACCESS EXCLUSIVE MODE;
        WITH RECURSIVE search_graph(part_of_id, subject_id, depth, path, cycle) AS (
                SELECT tt.part_of_id, t1.id, 1, ARRAY[t1.id], false FROM subjects t1
                LEFT JOIN subjects_subjects AS tt ON tt.subject_id=t1.id
                WHERE tt.left_at IS NULL
            UNION ALL
                SELECT g.part_of_id, g.subject_id, sg.depth + 1, path || g.subject_id, g.subject_id = ANY(path)
                FROM subjects_subjects g, search_graph sg
                WHERE g.part_of_id = sg.subject_id AND g.left_at IS NULL AND NOT cycle
        )
        SELECT INTO cycles COUNT(*) FROM search_graph WHERE cycle=true;
        RAISE NOTICE 'cycles: %%', cycles;
        IF cycles > 0 THEN
           RAISE EXCEPTION 'cycle';
        END IF;
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER check_subjects_subjects_cycle AFTER INSERT OR UPDATE ON subjects_subjects
        FOR EACH ROW EXECUTE PROCEDURE check_subjects_subjects_cycle();
""")
event.listen(t_subjects_subjects, 'after_create', t_subjects_subjects_ddl.execute_if(dialect='postgresql'))
#TODO: Add constraints that checks if ancestor is actually allowed by the ancestor hierarchy. (on update/insert of subject OR subjecttype)

# Authentication Stuff (user, role, permission system); Token based authentication

t_auth_users = Table("auth_users", Base.metadata,
    Column('id', ty.BigInteger, primary_key = True),
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="RESTRICT"), index=True, nullable=False),
    Column("email", ty.String, unique=True),
    Column("password_hash", ty.String, nullable=False),
    Column("password_salt", ty.Unicode, nullable=False),
    Column("force_password_change", ty.Boolean, nullable=False, server_default='0'),
    Column("active", ty.Boolean, nullable=False, index=True, server_default='1'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

def get_default_token_valid_time():
    return dt_ago(days=-30) # in 30 days

t_auth_tokens = Table("auth_tokens", Base.metadata,
    Column("id", ty.BigInteger, primary_key=True),
    Column("auth_user_id", ty.BigInteger, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
    Column("token", ty.String, nullable=False),
    Column('valid_until', TIMESTAMP(timezone=True), nullable=False, default=get_default_token_valid_time),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

t_auth_roles = Table("auth_roles", Base.metadata,
    Column("id", ty.Integer, primary_key=True),
    Column("name", ty.String(100), unique=True),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

t_auth_users_roles = Table("auth_users_roles", Base.metadata,
    Column("id", ty.BigInteger, primary_key=True),
    Column("auth_user_id", ty.BigInteger, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("auth_role_id", ty.Integer, ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True),
)

t_auth_roles_permissions = Table("auth_roles_permissions", Base.metadata,
    Column("id", ty.Integer, primary_key=True),
    Column("auth_role_id", ty.Integer, ForeignKey("auth_roles.id", use_alter=True, ondelete="CASCADE"), nullable=False, index=True),
    Column("name", ty.String(255), nullable=False), # taken from gengine.app.permissions
    UniqueConstraint("auth_role_id", "name")
)

# Directed relations (like friendships)
t_subjectrelations = Table("subjectrelations", Base.metadata,
    Column("id", ty.BigInteger, primary_key=True),
    Column('from_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('to_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
    UniqueConstraint("from_id", "to_id")
)

# Achievements can be categorized (for better organization in the client)
t_achievementcategories = Table('achievementcategories', Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    # The name is used to filter the achievements in the client and api requests
    Column('name', ty.String(255), nullable=False, unique=True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# Achievements! (The core of this application)
t_achievements = Table('achievements', Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    # Internal Use, external should be added by using a property
    Column('name', ty.String(255), nullable=False),

    # For ordering in the UI
    Column('priority', ty.Integer, index=True, default=0),

    # We assign the achievement to a category
    Column("achievementcategory_id", ty.Integer, ForeignKey("achievementcategories.id", ondelete="SET NULL"), index=True, nullable=True),

    # An achievement can have multiple levels. What is the maximum level? (For leaderboards this is typically always 1)
    Column('maxlevel', ty.Integer, nullable=False, default=1),

    # May the user see this achievement and the progress before it is reached?
    Column('hidden', ty.Boolean, nullable=False, default=False),

    # The achievement can be valid for only a specific time
    Column('valid_start', ty.Date, nullable=True),
    Column('valid_end', ty.Date, nullable=True),

    # The achievement can be constrained to geo-position (radius)
    Column("lat", ty.Float(Precision=64), nullable=True),
    Column("lng", ty.Float(Precision=64), nullable=True),
    Column("max_distance", ty.Integer, nullable=True),

    # Some achievements occur periodically. This fields defines when and how often they are evaluated.
    # "immediately" means, it is evaluated each time a value changes
    # "end" means, it is evaluated after "valid_end" is reached
    Column('evaluation', ty.Enum("immediately", "daily", "weekly", "monthly", "yearly", "end", name="evaluation_types"), default="immediately", nullable=False),

    # For time-related achievements, the timezone should be fixed im multiple subjects are involved (leaderboard), as otherwise the comparison is not in sync
    # For single-user achievements (no leaderboard), we can use the timezone of each subject
    Column('evaluation_timezone', ty.String(), default=None, nullable=True),

    # Weeks don't start on the same day everywhere and in every use-cases. Same for years, days and months.
    # We can shift them by a fixed amount of seconds!
    Column('evaluation_shift', ty.Integer(), nullable=True, default=None),

    # If this is just a normal achievement, we don't want to compare the value to other subjects
    # For leaderaboard, we need to define who is compared to whom:
    #   - global: the subject is compared to all other subjects of the same subjecttype
    #   - context_subject: the subject is compared inside the defined context_subjecttype.
    #     As the player can be part of multiple subjects of this type, the achievement can be evaluated and achieved for each of these subjects!
    #   - relations: The player is compared to all his relations (they are directed)
    #   - none: no leaderboard, just single achievement
    Column('comparison_type', ty.Enum("global", "context_subject", "relations", "none", name="comparison_types"), default="none"),

    # This one is the actual player, that will "win" the achievement
    Column('player_subjecttype_id', ty.Integer(), ForeignKey("subjecttypes.id", ondelete="CASCADE"), nullable=False, index=True),

    # If this is a leaderboard: In which group of subjects do we compare the current subject?
    # It may also make sense to compare the groups inbetween:
    #  - User is the Player
    #  - Country is the Context
    #  - We may also see how the team performs in comparison to other teams in the country (though the team cannot "achieve" anything)
    # These "compared subject types" are defined in the table achievement_compared_subjects
    Column('context_subjecttype_id', ty.Integer(), ForeignKey("subjecttypes.id", ondelete="RESTRICT"), nullable=True, index=True),

    # Do only members count, that have been part of the context subject for the whole time?
    # For achievements with a lower bound (geq) this will mostly be true, as a later joined user gets no advantage
    # For upper bound achievements ("do at most x times event e  in this month") a later joined user would have an advantage and this should be set to true
    Column('lb_subject_part_whole_time', ty.Boolean, nullable=False, default=False, server_default='0'),

    # Who may see this Achievement?
    Column('view_permission', ty.Enum("everyone", "own", name="achievement_view_permission"), default="everyone"),

    # filter condition for the event values that are aggregated for the achievement value
    Column('condition', ty.String(255), nullable=True),

    # How old may the values be, that are considered in this achievement?
    Column('timespan', ty.Integer, nullable=True),

    # We can group the values by a key or date (eg. achieve sth. on a sunday)
    Column('group_by_key', ty.Boolean(), default=False),
    Column('group_by_dateformat', ty.String(255), nullable=True),

    # The value that has to be achieved to be reached to achieve this / is NULL for pure leaderboards
    Column('goal', ty.String(255), nullable=True),

    # Is the goal value a lower or upper bound?
    Column('operator', ty.Enum("geq","leq", name="goal_operators"), nullable=True),

    # When we group by key or dateformat: Should we select the max or min value of the groups?
    Column('maxmin', ty.Enum("max","min", name="goal_maxmin"), nullable=True, default="max"),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now),
)

# Between the achievement player and the context, there can be other levels of comparison (e.g. compare the team instead of the user)
# These cannot achieve the achievement, but can only be looked at!
t_achievement_compared_subjecttypes = Table('achievement_compared_subjects', Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('subjecttype_id', ty.Integer, ForeignKey("subjecttypes.id", ondelete="CASCADE"), nullable=False, index=True),
    UniqueConstraint("achievement_id", "subjecttype_id")
)

# The achievements can be restricted to be valid inside a specific subject set (e.g. only in Germany)
# This restriction applies to the players, compared subjects and the context subjects
t_achievement_domain_subjects = Table('achievement_domain_subjects', Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True),
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
    UniqueConstraint("achievement_id", "subject_id")
)

# We store the evaluated values in a table to generate the leaderboard and return the achievement's progress efficiently
t_evaluations = Table("evaluations", Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    # For whom?
    Column("subject_id", ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),

    # Which achievement?
    Column("achievement_id", ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True),

    # For which period?
    Column('achievement_date', TIMESTAMP(timezone=True), nullable=True, index=True), # To identify the goals for monthly, weekly, ... achievements;

    # The current value
    Column("value", ty.Float, index=True, nullable=False),

    # Is this achieved?
    Column("achieved", ty.Boolean, nullable=False, server_default='0', default=False, index=True),

    # Which level is this
    Column('level', ty.Integer, default=0, nullable=False, index=True),
)

Index("idx_evaluations_date_not_null_unique",
    t_evaluations.c.subject_id,
    t_evaluations.c.achievement_id,
    t_evaluations.c.achievement_date,
    unique=True,
    postgresql_where=t_evaluations.c.achievement_date != None
)

Index("idx_evaluations_date_null_unique",
    t_evaluations.c.subject_id,
    t_evaluations.c.achievement_id,
    unique=True,
    postgresql_where=t_evaluations.c.achievement_date == None
)

# The event types that can happen. The types of values we use to construct achievements.
t_variables = Table('variables', Base.metadata,
    Column('id', ty.Integer, primary_key = True),

    # The name; is used by the API to increase the values
    Column('name', ty.String(255), nullable = False, index=True, unique=True),

    # Who may increase this? (API permissions)
    Column('increase_permission',ty.Enum("own", "admin", name="variable_increase_permission"), default="admin"),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# These are the actual values
t_values = Table('values', Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    # For whom we count the value
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False),

    # Who invoked the increasement?
    Column('agent_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=False),

    # When did it happen
    Column('datetime', TIMESTAMP(timezone=True), nullable=False, index=True, default=dt_now),

    # Which type of event happened?
    Column('variable_id', ty.Integer, ForeignKey("variables.id", ondelete="CASCADE"), index=True, nullable=False),

    # The value
    Column('value', ty.Float, nullable = False),

    # In which context did this happen (e.g. a product_id; s.th. unique to the application)
    Column('key', ty.String(100), nullable=False, index=True, default=''),
)

# Achievements can trigger things (like messages)
t_achievement_triggers = Table('achievement_triggers', Base.metadata,
   Column('id', ty.Integer, primary_key = True),

   # internal use only
   Column("name", ty.String(100), nullable=False),

   Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True),

   # Should this also be executed when the achievement is completed (e.g. a message like "10 events to go" should not be send if you do 20 events at once
   Column('execute_when_complete', ty.Boolean, nullable=False, server_default='0', default=False),

   Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# The triggers can be divided into multiple steps (e.g. 10 to go; 5 to go; 3 to go)
t_achievement_trigger_steps = Table('achievement_trigger_steps', Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('achievement_trigger_id', ty.Integer, ForeignKey("achievement_triggers.id", ondelete="CASCADE"), nullable=False, index=True),

    # the number of the step (order in which they are executed)
    Column('step', ty.Integer, nullable=False, default=0),

    # The condition type. currently we only support a percentage of the goal value
    Column('condition_type', ty.Enum("percentage", name="goal_trigger_condition_types"), default="percentage"),
    Column('condition_percentage', ty.Float, nullable=True),

    # type of action to execute (currently only creation of a message)
    Column('action_type', ty.Enum("subject_message", name="goal_trigger_action_types"), default="subject_message"),
    Column('action_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable=True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),

    UniqueConstraint("goal_trigger_id", "step")
)

# Which steps have already been executed. This is used to prevent duplicate executions.
t_achievement_trigger_step_executions = Table('achievement_trigger_executions', Base.metadata,
    Column('id', ty.BigInteger, primary_key=True),

    # Which step?
    Column('trigger_step_id', ty.Integer, ForeignKey("achievement_trigger_steps.id", ondelete="CASCADE"), nullable=False),

    # For whom?
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),

    # For which period?
    Column('achievement_date', TIMESTAMP(timezone=True), nullable=True, index=True),

    # For which level?
    Column('execution_level', ty.Integer, nullable = False, default=0),

    # When did the execution happen (autofilled)
    Column('execution_date', TIMESTAMP(timezone=True), nullable=False, default=datetime.datetime.utcnow, index=True),

    Index("ix_achievement_trigger_executions_combined", "trigger_step_id", "subject_id", "execution_level", "achievement_date")
)

# We can add properties to achievements, that are used to described them
# E.g. names, texts, urls to graphics etc.
# This table describes the types of properties that can be created
t_achievementproperties = Table('achievementproperties', Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    Column('name', ty.String(255), nullable=False, unique=True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# This are the instances.
t_achievements_achievementproperties = Table('achievements_achievementproperties', Base.metadata,
    Column('id', ty.Integer, primary_key = True),

    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), index=True, nullable=False),

    Column('property_id', ty.Integer, ForeignKey("achievementproperties.id", ondelete="CASCADE"), index=True, nullable=False),

    # Can be a formula...
    Column('value', ty.String(255), nullable = True),

    # ...or a text with translation
    Column('value_translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable=True),

    # Valid from which level (higher level overrides entries for lower levels)
    Column('from_level', ty.Integer, nullable=False, default=0, index=True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now),

    UniqueConstraint("achievement_id", "property_id", "from_level")
)

# There are two types of rewards for achievements:
# - (Rewards)       Rewards that are collected and can be achieved only once (like Badges, Backgrounds, etc.)
# - (Rewardpoints)  Points (like EXP) that are earned with every achievement / level
# This table described the available reward types...
t_rewards = Table('rewards', Base.metadata,
    Column('id', ty.Integer, primary_key = True),

    # For internal use and identification in frontend
    Column('name', ty.String(255), nullable = False, unique=True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),

    # Which subjecttype can collect this type of reward (user? team?)
    # If this is added to an achievement and the achievement player does not equal this subjecttype,
    # the path to this subjecttype is constructed and all relevant subjects are rewarded!
    Column('rewarded_subjecttype_id', ty.Integer(), ForeignKey("subjecttypes.id", ondelete="CASCADE"), nullable=False, index=True),
)

# Who inherits the rewarded items? When a team wins s.th, it's members might inherit the items...
# ..Or just the team as a whole gets it, and users who leave don't have it (depends on the application model)
t_reward_inheritors = Table('reward_inheritors', Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    Column('reward_id', ty.Integer, ForeignKey("rewards.id", ondelete="CASCADE"), nullable=False, index=True),

    Column('inheritor_subjecttype_id', ty.Integer(), ForeignKey("subjecttypes.id", ondelete="CASCADE"), nullable=False, index=True),

    UniqueConstraint("reward_id", "inheritor_subjecttype_id")
)

# What is rewarded by the achievements?
t_achievements_rewards = Table('achievements_rewards', Base.metadata,
    Column('id', ty.Integer, primary_key = True),

    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), index = True, nullable=False),

    Column('reward_id', ty.Integer, ForeignKey("rewards.id", ondelete="CASCADE"), index = True, nullable=False),

    # Can be a computed value or can be a translation
    Column('value', ty.String(255), nullable = True),
    Column('value_translation_id', ty.Integer, ForeignKey("translationvariables.id"), nullable = True),

    # Valid from which level (higher level overrides entries for lower levels)
    Column('from_level', ty.Integer, nullable = False, default=1, index = True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),

    UniqueConstraint("achievement_id", "reward_id", "from_level")
)

# Same as above for the second type of rewards (Points (like EXP) that are earned with every achievement / level)
t_rewardpoints = Table('rewardpoints', Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('name', ty.String(255), nullable=False, unique=True),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# Who inherits the rewarded points? When a team wins s.th, it's members might inherit the points...
# ..Or just the team as a whole gets it, and users who leave don't have it (depends on the application model)
t_rewardpoint_inheritors = Table('rewardpoint_inheritors', Base.metadata,
    Column('id', ty.Integer, primary_key=True),

    Column('rewardpoint_id', ty.Integer, ForeignKey("rewardpoints.id", ondelete="CASCADE"), nullable=False, index=True),

    Column('inheritor_subjecttype_id', ty.Integer(), ForeignKey("subjecttypes.id", ondelete="CASCADE"), nullable=False, index=True),

    UniqueConstraint("rewardpoint_id", "inheritor_subjecttype_id")
)

# What points are rewarded by the achievements?
t_achievements_rewardpoints = Table('achievements_rewardpoints', Base.metadata,
    Column('id', ty.Integer, primary_key = True),

    Column('achievement_id', ty.Integer, ForeignKey("achievements.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('rewardpoint_id', ty.Integer, ForeignKey("rewardpoints.id", ondelete="CASCADE"), index=True, nullable=False),

    # This is a formula that must evaluate to an integer because the result is backpopulated to the values table!
    Column('value', ty.String(255), nullable = True),

    # Valid from which level (higher level overrides entries for lower levels)
    Column('from_level', ty.Integer, nullable=False, default=1, index=True),

    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),

    UniqueConstraint("achievement_id", "rewardpoint_id", "from_level")
)

# The languages for which we want to provide translations.
t_languages = Table('languages', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False, index=True),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# Translation variables
t_translationvariables = Table('translationvariables', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('name', ty.String(255), nullable = False, index=True),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

# The translation values
t_translations = Table('translations', Base.metadata,
    Column('id', ty.Integer, primary_key = True),
    Column('translationvariable_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="CASCADE"), nullable = False),
    Column('language_id', ty.Integer, ForeignKey("languages.id", ondelete="CASCADE"), nullable = False),
    # The translation
    Column('text', ty.Text(), nullable=False),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
    UniqueConstraint("translationvariable_id", "language_id")
)

# This probably only makes sense for user-subjects, but lets keep it general
t_subject_device = Table('subject_devices', Base.metadata,
    Column('device_id', ty.String(255), primary_key = True),
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key = True, nullable=False),
    Column('device_os', ty.String, nullable=False),
    Column('push_id', ty.String(255), nullable=False),
    Column('app_version', ty.String(255), nullable=False),
    Column('registered_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now),
)

# This probably only makes sense for user-subjects, but lets keep it general
t_subject_messages = Table('subject_messages', Base.metadata,
    Column('id', ty.BigInteger, primary_key=True),
    Column('subject_id', ty.BigInteger, ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('translation_id', ty.Integer, ForeignKey("translationvariables.id", ondelete="RESTRICT"), nullable=True),
    Column('params', JSON(), nullable=True, default={}),
    Column('is_read', ty.Boolean, index=True, default=False, nullable=False),
    Column('has_been_pushed', ty.Boolean, index=True, default=True, server_default='0', nullable=False),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

t_tasks = Table('tasks', Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('entry_name', ty.String(100), index=True),
    Column('task_name', ty.String(100), index=True, nullable=False),
    Column('config', ty.JSON()),
    Column('cron', ty.String(100)),
    Column('is_removed', ty.Boolean, index=True, nullable=False, default=False),
    Column('is_auto_created', ty.Boolean, index=True, nullable=False, default=False),
    Column('is_manually_modified', ty.Boolean, index=True, nullable=False, default=False),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)

t_taskexecutions = Table('taskexecutions', Base.metadata,
    Column('id', ty.Integer, primary_key=True),
    Column('task_id', ty.Integer, ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False),
    Column('planned_at', TIMESTAMP(timezone=True), nullable=False, default=None, index=True),
    Column('locked_at', TIMESTAMP(timezone=True), nullable=True, default=None, index=True),
    Column('finished_at', TIMESTAMP(timezone=True), nullable=True, default=None, index=True),
    Column('canceled_at', TIMESTAMP(timezone=True), nullable=True, default=None, index=True),
    Column('log', ty.String),
    Column('success', ty.Boolean, index=True, nullable=True, default=None),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=dt_now, index=True),
)


#class EvaluationContext:
#    def __init__(self, context_subject_id, achievment_date):
#        self.context_subject_id = context_subject_id
#        self.achievement_date = achievment_date


class AuthUser(ABase):

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

    @classmethod
    def check_password_strength(cls, password):
        length_error = len(password) < 8
        return not length_error

    def get_or_create_token(self):
        tokenObj = DBSession.query(AuthToken).filter(and_(
            AuthToken.valid_until >= dt_now(),
            AuthToken.subject_id == self.subject_id,
            AuthToken.deleted_at == None
        )).first()

        if not tokenObj:
            token = AuthToken.generate_token()
            tokenObj = AuthToken(
                subject_id=self.subject_id,
                token=token
            )

            DBSession.add(tokenObj)

        return tokenObj

    @classmethod
    def may_increase(cls, variable_row, request, auth_user_id):
        if not asbool(get_settings().get("enable_user_authentication", False)):
            #Authentication deactivated
            return True
        if request.has_perm(perm_global_increase_value):
            # I'm the global admin
            return True
        if variable_row["increase_permission"] == "own" and request.user and str(request.user.id) == str(auth_user_id):
            #The variable may be updated for myself
            return True
        return False

class AuthToken(ABase):

    @staticmethod
    def generate_token():
        import crypt
        return str(crypt.mksalt()+crypt.mksalt())

    def extend(self):
        self.valid_until = dt_in(days=30)
        DBSession.add(self)

    def __unicode__(self, *args, **kwargs):
        return "Token %s" % (self.id,)

class AuthRole(ABase):
    def __unicode__(self, *args, **kwargs):
        return "Role %s" % (self.name,)

class AuthRolePermission(ABase):
    def __unicode__(self, *args, **kwargs):
        return "%s" % (self.name,)

class SubjectDevice(ABase):
    def __unicode__(self, *args, **kwargs):
        return "Device: %s" % (self.device_id,)

    @classmethod
    def add_or_update_device(cls, subject_id, device_id, push_id, device_os, app_version):
        update_connection().execute(t_subject_device.delete().where(and_(
            t_subject_device.c.push_id == push_id,
            t_subject_device.c.device_os == device_os
        )))

        device = DBSession.execute(t_subject_device.select().where(and_(
            t_subject_device.c.device_id == device_id,
            t_subject_device.c.subject_id == subject_id
        ))).fetchone()

        if device and (device["push_id"] != push_id
            or device["device_os"] != device_os
            or device["app_version"] != app_version
        ):
            uSession = update_connection()
            q = t_subject_device.update().values({
                "push_id": push_id,
                "device_os": device_os,
                "app_version": app_version
            }).where(and_(
                t_subject_device.c.device_id == device_id,
                t_subject_device.c.subject_id == subject_id
            ))
            uSession.execute(q)
        elif not device:  # insert
            uSession = update_connection()
            q = t_subject_device.insert().values({
                "push_id": push_id,
                "device_os": device_os,
                "app_version": app_version,
                "device_id": device_id,
                "subject_id": subject_id
            })
            uSession.execute(q)

class Subject(ABase):
    """A subject participates in the gamification, i.e. can get achievements, rewards, participate in leaderbaord etc."""

    def __unicode__(self, *args, **kwargs):
        return "Subject %s" % (self.id,)

    def __init__(self, *args, **kw):
        """ create a subject object

        Each subject has a timezone and a location to support time- and geo-aware gamification.
        There is also a subject-relation for leaderboards and a hierarchical subject-subject structure.
        """
        ABase.__init__(self, *args, **kw)

    @classmethod
    def get_subject(cls,subject_id):
        return DBSession.execute(t_subjects.select().where(t_subjects.c.id == subject_id)).fetchone()

    @classmethod
    def get_subjects(cls, subject_ids):
        return {
            x["id"] : x for x in
            DBSession.execute(t_subjects.select().where(t_subjects.c.id.in_(subject_ids))).fetchall()
        }

    @classmethod
    def set_relations(cls, subject_id, relation_ids):

        new_friends_set = set(relation_ids)
        existing_subjects_set = {x["id"] for x in DBSession.execute(select([t_subjects.c.id]).where(t_subjects.c.id.in_([subject_id, ] + relation_ids))).fetchall()}
        existing_friends = {x["to_id"] for x in DBSession.execute(select([t_subjectrelations.c.to_id]).where(t_subjectrelations.c.from_id==subject_id)).fetchall()}
        not_existing_friends = (new_friends_set-existing_subjects_set-{subject_id,})
        friends_to_append = ((new_friends_set - existing_friends) - not_existing_friends)
        friends_to_delete = ((existing_friends - new_friends_set) - not_existing_friends)

        #delete old friends
        if len(friends_to_delete)>0:
            update_connection().execute(t_subjectrelations.delete().where(and_(t_subjectrelations.c.from_id==subject_id,
                                                                               t_subjectrelations.c.to_id.in_(friends_to_delete))))
        #insert missing friends
        if len(friends_to_append)>0:
            update_connection().execute(t_subjectrelations.insert(),[{"from_id":subject_id,"to_id":f} for f in friends_to_append])

    @classmethod
    def set_parent_subjects(cls, subject_id, parent_subject_ids):
        pass

    @classmethod
    def set_infos(cls, subject_id, lat, lng, timezone, language_id, additional_public_data):
        """set the subject's metadata like friends,location and timezone"""

        # add or select subject
        subject = DBSession.query(Subject).filter_by(id=subject_id).first()
        subject.lat = lat
        subject.lng = lng
        subject.timezone = timezone
        subject.additional_public_data = additional_public_data
        subject.language_id = language_id
        DBSession.add(subject)
        DBSession.flush()

    @classmethod
    def delete_subject(cls,subject_id):
        """delete a subject including all dependencies."""
        update_connection().execute(t_evaluations.delete().where(t_evaluations.c.subject_id == subject_id))
        update_connection().execute(t_subjectrelations.delete().where(t_subjectrelations.c.to_id==subject_id))
        update_connection().execute(t_subjectrelations.delete().where(t_subjectrelations.c.from_id==subject_id))
        update_connection().execute(t_subjects_subjects.delete().where(t_subjects_subjects.c.subject_id==subject_id))
        update_connection().execute(t_subjects_subjects.delete().where(t_subjects_subjects.c.part_of_id==subject_id))
        update_connection().execute(t_values.delete().where(t_values.c.subject_id==subject_id))
        update_connection().execute(t_subjects.delete().where(t_subjects.c.id == subject_id))

    @classmethod
    def basic_output(cls, subject):
        return {
            "id": subject["id"],
            "name": subject["name"],
            "additional_public_data": subject["additional_public_data"]
        }

    @classmethod
    def full_output(cls, subject_id):

        subject = DBSession.execute(t_subjects.select().where(t_subjects.c.id == subject_id)).fetchone()

        j = t_subjects.join(t_subjectrelations, t_subjectrelations.c.to_id == t_subjects.c.id)
        friends = DBSession.execute(t_subjects.select(from_obj=j).where(t_subjectrelations.c.from_id == subject_id)).fetchall()

        j = t_subjects.join(t_subjects_subjects)
        part_of_subjects = DBSession.execute(t_subjects.select(from_obj=j).where(t_subjects_subjects.c.subject_id == subject_id)).fetchall()

        language = get_settings().get("fallback_language","en")
        j = t_subjects.join(t_languages)
        subject_language = DBSession.execute(select([t_languages.c.name], from_obj=j).where(t_subjects.c.id == subject_id)).fetchone()
        if subject_language:
            language = subject_language["name"]

        ret = {
            "id": subject["id"],
            "lat": subject["lat"],
            "lng": subject["lng"],
            "timezone": subject["timezone"],
            "language": language,
            "created_at": subject["created_at"],
            "additional_public_data": subject["additional_public_data"],
            "relations": [Subject.basic_output(f) for f in friends],
            "part_of": [Subject.basic_output(g) for g in part_of_subjects],
        }

        if get_settings().get("enable_user_authentication"):
            auth_user = DBSession.execute(t_auth_users.select().where(t_auth_users.c.subject_id == subject_id)).fetchone()
            if auth_user:
                ret.update({
                    "email" : auth_user["email"]
                })

        return ret

    @classmethod
    def get_ancestor_subjects(cls, subject_id, of_type_id, from_date, to_date, whole_time_required):
        if whole_time_required:
            datestr = "(%(ss)s.joined_at<=:from_date AND (%(ss)s.left_at IS NULL OR %(ss)s.left_at >= :to_date))"
        else:
            datestr = "((%(ss)s.joined_at<=:from_date AND (%(ss)s.left_at IS NULL OR %(ss)s.left_at >= :from_date))" \
                      "OR (%(ss)s.joined_at >= :from_date AND %(ss)s.joined_at <= :to_date)" \
                      "OR (%(ss)s.left_at >= :from_date AND %(ss)s.left_at <= :to_date))"

        sq = text("""
            WITH RECURSIVE nodes_cte(subject_id, name, part_of_id, depth, path) AS (
                SELECT g1.id, g1.name, NULL::bigint as part_of_id, 1::INT as depth, g1.id::TEXT as path
                FROM subjects as g1
                OUTER JOIN subjects_subjects ss ON ss.subject_id=g1.id
                WHERE ss.subject_id = :subject_id AND """+(datestr % {'ss': 'ss'})+"""
            UNION ALL
                SELECT c.subject_id, g2.name, c.part_of_id, p.depth + 1 AS depth,
                    (p.path || '->' || g2.id ::TEXT)
                FROM nodes_cte AS p, subjects_subjects AS c
                JOIN subjects AS g2 ON g2.id=c.subject_id
                WHERE p.part_of_id = c.subject_id AND """+(datestr % {'ss': 'c'})+"""
            ) SELECT * FROM nodes_cte
        """).bindparams(subject_id=subject_id, from_date=from_date, to_date=to_date).columns(subject_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()

        j = t_subjects.join(sq, sq.c.subject_id == t_subjects.c.id)

        q = select([
            sq.c.path.label("subject_path"),
            sq.c.subject_id.label("subject_id"),
            sq.c.name.label("subject_name"),
            t_subjects.c.subjecttype_id.label("subjecttype_id")
        ], from_obj=j)

        if of_type_id is not None:
            q = q.where(t_subjects.c.subjecttype_id == of_type_id)

        rows = DBSession.execute(q).fetchall()
        groups = {r["part_of_id"]: r for r in rows if r["part_of_id"]}
        return groups

    @classmethod
    def get_descendent_subjects(cls, subject_id, of_type_id, from_date, to_date, whole_time_required):
        if whole_time_required:
            datestr = "(%(ss)s.joined_at<=:from_date AND (%(ss)s.left_at IS NULL OR %(ss)s.left_at >= :to_date))"
        else:
            datestr = "((%(ss)s.joined_at<=:from_date AND (%(ss)s.left_at IS NULL OR %(ss)s.left_at >= :from_date))" \
                      "OR (%(ss)s.joined_at >= :from_date AND %(ss)s.joined_at <= :to_date)" \
                      "OR (%(ss)s.left_at >= :from_date AND %(ss)s.left_at <= :to_date))"

        sq = text("""
            WITH RECURSIVE nodes_cte(subject_id, name, part_of_id, depth, path) AS (
                SELECT g1.id, g1.name, NULL::bigint as part_of_id, 1::INT as depth, g1.id::TEXT as path
                FROM subjects as g1
                OUTER JOIN subjects_subjects ss ON ss.subject_id=g1.id
                WHERE ss.part_of_id = :subject_id AND """+(datestr % {'ss': 'ss'})+"""
            UNION ALL
                SELECT c.subject_id, g2.name, c.part_of_id, p.depth + 1 AS depth,
                    (p.path || '->' || g2.id ::TEXT)
                FROM nodes_cte AS p, subjects_subjects AS c
                JOIN subjects AS g2 ON g2.id=c.subject_id
                WHERE c.part_of_id = p.subject_id AND """+(datestr % {'ss': 'c'})+"""
            ) SELECT * FROM nodes_cte
        """).bindparams(subject_id=subject_id, from_date=from_date, to_date=to_date).columns(subject_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()

        j = t_subjects.join(sq, sq.c.subject_id == t_subjects.c.id)

        q = select([
            sq.c.path.label("subject_path"),
            sq.c.subject_id.label("subject_id"),
            sq.c.name.label("subject_name"),
            t_subjects.c.subjecttype_id.label("subjecttype_id")
        ], from_obj=j)

        if of_type_id is not None:
            q = q.where(t_subjects.c.subjecttype_id == of_type_id)

        rows = DBSession.execute(q).fetchall()
        subjects = {r["subject_id"]: r for r in rows if r["subject_id"]}
        return subjects


class SubjectType(ABase):
    def __unicode__(self, *args, **kwargs):
        return "(ID: %s; Name: %s)" % (self.id, self.name)

    @classmethod
    def basic_output(cls, subjecttype):
        return {
            "id": subjecttype["id"],
            "name": subjecttype["name"],
        }

class Variable(ABase):
    """A Variable is anything that should be meassured in your application and be used in :class:`.Goal`.

       To save database rows, variables may be grouped by time:
       group needs to be set to "year","month","day","timeslot" or "none" (default)
    """

    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

    @classmethod
    @cache_general.cache_on_arguments()
    def get_variable_by_name(cls,name):
        return DBSession.execute(t_variables.select(t_variables.c.name==name)).fetchone()

    @classmethod
    @cache_general.cache_on_arguments()
    def map_variables_to_rules(cls):
        """return a map from variable_ids to [achievement1,..] lists.
           Used to know which achievements need to be reevaluated after a value for the variable changes."""
        q = select([t_achievements.c.id.label("achievement_id"), t_variables.c.id.label("variable_id")])\
            .where(or_(t_achievements.c.condition.ilike(func.concat('%"',t_variables.c.name,'"%')),
                       t_achievements.c.condition.ilike(func.concat("%'",t_variables.c.name,"'%"))))
        rows = DBSession.execute(q).fetchall()
        achievements = { a["achievement_id"] : Achievement.get_achievement(a["achievement_id"]) for a in { r["achievement_id"] for r in rows } }
        m={}
        for row in rows:
            if not row["variable_id"] in m:
                m[row["variable_id"]] = []

            m[row["variable_id"]].append(achievements[row["achievement_id"]])
        return m


class Value(ABase):
    """A Value describes the relation of the subject to a variable.
    (e.g. it counts the occurences of the "events" which the variable represents) """

    @classmethod
    def increase_value(cls, variable_name, subject, value, key, at_datetime):
        """increase the value of the variable for the subject.

        In addition to the variable_name there may be an application-specific key which can be used in your :class:`.Achievement` definitions
        The parameter at_datetime is optional and can specify a timezone-aware datetime to define when the event happened
        """

        subject_id = subject["id"]
        variable = Variable.get_variable_by_name(variable_name)
        key = normalize_key(key)
        part_of_ids = list(Subject.get_groups(subject_id).keys())

        sid_set = set([subject_id, ] + part_of_ids)

        # Populate the value for all relevant subjects:

        for sid in sid_set:
            condition = and_(t_values.c.datetime == at_datetime,
                             t_values.c.variable_id == variable["id"],
                             t_values.c.subject_id == sid,
                             t_values.c.agent_id == subject_id,
                             t_values.c.key == key)

            current_value = DBSession.execute(select([t_values.c.value,]).where(condition)).scalar()
            if current_value is not None:
                update_connection().execute(t_values.update(condition, values={"value":current_value+value}))
            else:
                update_connection().execute(t_values.insert({"datetime": at_datetime,
                                               "variable_id": variable["id"],
                                               "subject_id": sid,
                                               "agent_id": subject_id,
                                               "key": key,
                                               "value": value}))

        # Clear the relevant achievement caches!

        achievements = cls.map_variables_to_rules().get(variable["id"], [])

        achievement_id_to_achievement_date = {
            entry["id"]: AchievementDate.compute(
                evaluation_timezone=entry["evaluation_timezone"],
                evaluation_type=entry["evaluation"],
                context_datetime=at_datetime,
                evaluation_shift=entry["evaluation_shift"]
            ) for entry in achievements
        }

        # get the subjects...
        subjects = {}
        for sid in sid_set:
            subjects[sid] = Subject.get_ancestor_subjects(
                subject_id=sid,
                of_type_id=None,
                from_date=at_datetime,
                to_date=at_datetime,
                whole_time_required=False
            )

        for sid in sid_set:
            for achievement in achievements:
                achievement_date = achievement_id_to_achievement_date[achievement["id"]]
                compared_subjects = [s for s in subjects[sid] if s["subjecttype_id"] in achievement["compared_subjecttypes"]]
                for compared_subject in compared_subjects:
                    q = t_evaluations.delete().where(and_(
                        t_evaluations.c.subject_id == compared_subject["subject_id"],
                        t_evaluations.c.achievement_id == achievement["id"],
                        t_evaluations.c.achievement_date == achievement_date,
                        t_evaluations.c.achieved == False,
                    ))
                    update_connection().execute(q)


class AchievementCategory(ABase):
    """A category for grouping achievement types"""

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievementcategory(cls, achievementcategory_id):
        return DBSession.execute(t_achievementcategories.select().where(t_achievementcategories.c.id==achievementcategory_id)).fetchone()

    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)


class AchievementDate:
    def __init__(self, from_date, to_date):
        self.from_date = from_date
        self.to_date = to_date

    def __repr__(self):
        return "AchievementDate(%s, %s)" % (str(self.from_date), str(self.to_date))

    def __str__(self):
        return self.from_date.isoformat()

    def __json__(self, *args, **kw):
        return self.from_date.isoformat()

    @classmethod
    def db_format(cls, instance):
        return instance.from_date if instance else None

    @classmethod
    def compute(cls, evaluation_timezone, evaluation_type, evaluation_shift, context_datetime):
        """
            This computes the datetime to identify the time of the achievement.
            Only relevant for repeating achievements (monthly, yearly, weekly, daily)
            Returns None for all other achievement types
        """

        if evaluation_type and not evaluation_timezone:
            evaluation_timezone = "UTC"

        tzobj = pytz.timezone(evaluation_timezone)
        if not context_datetime:
            dt = datetime.datetime.now(tzobj)
        else:
            dt = context_datetime.astimezone(tzobj)

        from_date = dt
        to_date = dt
        if evaluation_type == "yearly":
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) - datetime.timedelta(seconds=evaluation_shift)))
            from_date = from_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) + datetime.timedelta(seconds=evaluation_shift)))
            to_date = from_date + relativedelta(years=1)
        elif evaluation_type == "monthly":
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) - datetime.timedelta(seconds=evaluation_shift)))
            from_date = from_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) + datetime.timedelta(seconds=evaluation_shift)))
            to_date = from_date + relativedelta(months=1)
        elif evaluation_type == "weekly":
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) - datetime.timedelta(seconds=evaluation_shift)))
            from_date = from_date - datetime.timedelta(days=from_date.weekday())
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) + datetime.timedelta(seconds=evaluation_shift)))
            to_date = from_date + relativedelta(weeks=1)
        elif evaluation_type == "daily":
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) - datetime.timedelta(seconds=evaluation_shift)))
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if evaluation_shift:
                from_date = tzobj.localize((from_date.replace(tzinfo=None) + datetime.timedelta(seconds=evaluation_shift)))
            to_date = from_date + relativedelta(days=1)
        elif evaluation_type == "immediately":
            return None
        elif evaluation_type == "end":
            return None

        return AchievementDate(
            from_date = from_date.astimezone(tzobj),
            to_date = to_date.astimezone(tzobj)
        )



class Achievement(ABase):
    """A collection of goals which has multiple :class:`AchievementProperty` and :class:`Reward`."""

    def __unicode__(self, *args, **kwargs):
        return self.name + " (ID: %s)" % (self.id,)

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievement(cls,achievement_id):
        achievement = DBSession.execute(t_achievements.select().where(t_achievements.c.id == achievement_id)).fetchone()
        compared_subjecttypes = DBSession.execute(t_achievement_compared_subjecttypes.select().where(t_achievement_compared_subjecttypes.c.achievement_id == achievement_id)).fetchall()
        domain_subjects = DBSession.execute(t_achievement_compared_subjecttypes.select().where(t_achievement_compared_subjecttypes.c.achievement_id == achievement_id)).fetchall()

        achievement['compared_subjecttypes'] = compared_subjecttypes
        achievement['domain_subjects'] = domain_subjects

        return achievement

    @classmethod
    def get_achievements_by_subject_for_today(cls,subject):
        """Returns all achievements that are relevant for the subject today.

        This is needed as achievements may be limited to a specific time (e.g. only during holidays)
        """

        def generate_achievements_by_subject_for_today():
            today = datetime.date.today()
            by_loc = {x["id"] : x["distance"] for x in cls.get_achievements_by_location(coords(subject))}
            by_date = cls.get_achievements_by_date(today)
            def update(arr,distance):
                arr["distance"]=distance
                return arr

            return [update(arr,by_loc[arr["id"]]) for arr in by_date if arr["id"] in by_loc]

        key = str(subject["id"])
        expiration_time = Subject.get_cache_expiration_time_for_today(subject)

        return cache_achievements_by_subject_for_today.get_or_create(key,generate_achievements_by_subject_for_today, expiration_time=expiration_time)

    #We need to fetch all achievement data in one of these methods -> by_date is just queried once a date

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievements_by_location(cls,latlng):
        """return achievements which are valid in that location."""
        #TODO: invalidate automatically when achievement in subject's range is modified
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
        q = t_achievements.select().where(and_(or_(t_achievements.c.valid_start == None,
                                                   t_achievements.c.valid_start <= date),
                                               or_(t_achievements.c.valid_end == None,
                                                   t_achievements.c.valid_end >= date)
                                               ))

        return [dict(x.items()) for x in DBSession.execute(q).fetchall() if len(Goal.get_goals(x['id']))>0]

    @classmethod
    def get_relevant_subjects_by_achievement_and_subject(cls, achievement, subject, context_subject_id, from_date, to_date):
        """
        return all relevant other subjects for the leaderboard. This method is used for collecting all subjects for the output. the reverse method is used to clear the caches properly
        depends on the "relevance" attribute of the achievement, can be "friends", "global" or "context_subject"
        """
        # this is needed to compute the leaderboards
        #subjects=[subject_id,]

        from gengine.app.leaderboard import FriendsLeaderBoardSubjectSet, GlobalLeaderBoardSubjectSet, \
            ContextSubjectLeaderBoardSubjectSet

        subjects=[]

        if achievement["relevance"] == "friends":
            subjects = FriendsLeaderBoardSubjectSet.forward(
                subject_id=subject["id"],
                from_date=from_date,
                to_date=to_date,
                whole_time_required=achievement["lb_subject_part_whole_time"]
            )
        elif achievement["relevance"] == "global":
            subjects = GlobalLeaderBoardSubjectSet.forward(
                from_date=from_date,
                to_date=to_date,
                whole_time_required=achievement["lb_subject_part_whole_time"]
            )
        elif achievement["relevance"] == "context_subject":
            subjects = ContextSubjectLeaderBoardSubjectSet.forward(
                subject_type_id=subject["subjecttype_id"],
                context_subject_id=context_subject_id,
                from_date=from_date,
                to_date=to_date,
                whole_time_required=achievement["lb_subject_part_whole_time"]
            )

        return set(subjects)

    @classmethod
    def get_level(cls, subject_id, achievement_id, achievement_date):
        """get the current level of the subject for this achievement."""
        def generate():
            q = select([t_achievements_subjects.c.level,
                        t_achievements_subjects.c.achievement_date,
                        t_achievements_subjects.c.updated_at],
                       and_(t_achievements_subjects.c.subject_id == subject_id,
                            t_achievements_subjects.c.achievement_date == AchievementDate.db_format(achievement_date),
                            t_achievements_subjects.c.achievement_id == achievement_id)).order_by(t_achievements_subjects.c.level.desc())
            return [x for x in DBSession.execute(q).fetchall()]
        return cache_achievements_subjects_levels.get_or_create("%s_%s_%s" % (subject_id, achievement_id, str(achievement_date)), generate)

    @classmethod
    def get_level_int(cls, subject_id, achievement_id, achievement_date):
        """get the current level of the subject for this achievement as int (0 if the user does not have this achievement)"""
        lvls = Achievement.get_level(subject_id, achievement_id, achievement_date)
        if not lvls:
            return 0
        else:
            return lvls[0]["level"]

    @classmethod
    def basic_output(cls, achievement, goals, include_levels=True, max_level_included=None):
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
                max_level_included = min(max_level_included, levellimit)

            out["levels"] = {
                str(i): {
                    "level": i,
                    "goals": {str(g["id"]): Goal.basic_goal_output(g, i) for g in goals},
                    "rewards": {str(r["id"]): {
                        "id": r["id"],
                        "reward_id": r["reward_id"],
                        "name": r["name"],
                        "value": evaluate_string(r["value"], {"level": i}),
                        "value_translated": Translation.trs(r["value_translation_id"], {"level": i}),
                    } for r in Achievement.get_rewards(achievement["id"], i)},
                    "properties": {str(r["property_id"]): {
                        "property_id": r["property_id"],
                        "name": r["name"],
                        "value": evaluate_string(r["value"], {"level": i}),
                        "value_translated": Translation.trs(r["value_translation_id"], {"level": i}),
                    } for r in Achievement.get_achievement_properties(achievement["id"], i)}
            } for i in range(1, max_level_included+1)}
        return out

    @classmethod
    def evaluate(cls, subject, achievement_id, achievement_date, execute_triggers=True, context_subject_id=None):
        """evaluate the achievement including all its subgoals for the subject.
           return the basic_output for the achievement plus information about the new achieved levels
        """
        def generate():
            achievement = Achievement.get_achievement(achievement_id)

            subject_id = subject["id"]
            subject_ids = Achievement.get_relevant_subjects_by_achievement_and_subject(
                achievement=achievement,
                subject=subject,
                context_subject_id=context_subject_id,
                from_date=achievement_date.from_date if achievement_date else None,
                to_date=achievement_date.to_date if achievement_date else None
            )

            subject_has_level = Achievement.get_level_int(
                subject_id=subject_id,
                achievement_id=achievement["id"],
                achievement_date=achievement_date
            )

            subject_wants_level = min((subject_has_level or 0)+1, achievement["maxlevel"])

            goal_evals = {}
            all_goals_achieved = True
            goals = Goal.get_goals(achievement["id"])
            for goal in goals:
                goal_eval = Goal.get_goal_eval_cache(
                    goal_id=goal["id"],
                    achievement_date=achievement_date,
                    subject_id=subject_id
                )
                if not goal_eval:
                    Goal.evaluate(
                        goal=goal,
                        achievement=achievement,
                        achievement_date=achievement_date,
                        subject=subject,
                        level=subject_wants_level,
                        goal_eval_cache_before=None,
                        execute_triggers=execute_triggers
                    )
                    goal_eval = Goal.get_goal_eval_cache(
                        goal_id=goal["id"],
                        achievement_date=achievement_date,
                        subject_id=subject_id
                    )

                if achievement["relevance"] in ("friends", "global", "context_subject"):
                    goal_eval["leaderboard"] = Goal.get_leaderboard(
                        goal=goal,
                        achievement_date=achievement_date,
                        subject_ids=subject_ids
                    )
                    own_filter = list(filter(lambda x: x["subject"]["id"] == subject_id, goal_eval["leaderboard"]))
                    if len(own_filter)>0:
                        goal_eval["leaderboard_position"] = own_filter[0]["position"]
                    else:
                        goal_eval["leaderboard_position"] = None

                goal_evals[goal["id"]]=goal_eval
                if not goal_eval["achieved"]:
                    all_goals_achieved = False

            output = ""
            new_level_output = None
            last_recursion_step = True # will be false, if the full basic_output is generated in a recursion step

            if all_goals_achieved and subject_has_level < achievement["maxlevel"]:
                #NEW LEVEL YEAH!

                new_level_output = {
                    "rewards": {
                        str(r["id"]): {
                            "id": r["id"],
                            "reward_id": r["reward_id"],
                            "name": r["name"],
                            "value": evaluate_string(r["value"], {"level": subject_wants_level}),
                            "value_translated": Translation.trs(r["value_translation_id"], {"level": subject_wants_level}),
                        } for r in Achievement.get_rewards(achievement["id"], subject_wants_level)
                     },
                    "properties": {
                        str(r["property_id"]): {
                            "property_id": r["property_id"],
                            "name": r["name"],
                            "is_variable": r["is_variable"],
                            "value": evaluate_string(r["value"], {"level": subject_wants_level}),
                            "value_translated": Translation.trs(r["value_translation_id"], {"level": subject_wants_level})
                        } for r in Achievement.get_achievement_properties(achievement["id"], subject_wants_level)
                    },
                    "level": subject_wants_level
                }

                for prop in new_level_output["properties"].values():
                    if prop["is_variable"]:
                        Value.increase_value(prop["name"], subject, prop["value"], achievement_id)

                update_connection().execute(t_achievements_subjects.insert().values({
                    "subject_id": subject_id,
                    "achievement_id": achievement["id"],
                    "achievement_date": AchievementDate.db_format(achievement_date),
                    "level": subject_wants_level
                }))

                #invalidate getter
                cache_achievements_subjects_levels.delete("%s_%s_%s" % (subject_id, achievement_id, str(achievement_date)))

                subject_has_level = subject_wants_level
                subject_wants_level = subject_wants_level+1

                Goal.clear_subject_goal_caches(subject_id, [(g["goal_id"], achievement_date) for g in goal_evals.values()])
                #the level has been updated, we need to do recursion now...
                #but only if there are more levels...
                if subject_has_level < achievement["maxlevel"]:
                    output = generate()
                    last_recursion_step = False

            if last_recursion_step: #is executed, if this is the last recursion step
                output = Achievement.basic_output(achievement, goals, True, max_level_included=subject_has_level+1)
                output.update({
                   "level": subject_has_level,
                   "levels_achieved": {
                        str(x["level"]): x["updated_at"] for x in Achievement.get_level(subject_id, achievement["id"], achievement_date)
                    },
                   "maxlevel": achievement["maxlevel"],
                   "new_levels": {},
                   "goals": goal_evals,
                   "achievement_date": achievement_date,
                })

            if new_level_output is not None: #if we reached a new level in this recursion step, add the previous levels rewards and properties
                output["new_levels"][str(subject_has_level)] = new_level_output

            return output

        return generate()
        #return cache_achievement_eval.get_or_create("%s_%s_%s_%s" % (subject["id"], achievement_id, achievement_date, context_subject_id), generate)

    #@classmethod
    #def invalidate_evaluate_cache(cls, subject_id, achievement, achievement_date):
    #    """
    #        This method is called to invalidate the achievement evaluation output when a value is increased.
    #        For leaderboards this means, that we need to reset the achievement evaluation output for all other subjects in that leaderboard!
    #    """
    #
    #    #We neeed to invalidate for all relevant users because of the leaderboards
    #    for user_id, user_meta in Achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user_id).items():
    #        group_ids = user_meta.get("groups", {None,})
    #        for gid in group_ids:
    #            cache_achievement_eval.delete("%s_%s_%s_%s" % (user_id, achievement["id"], achievement_date, gid))

    @classmethod
    @cache_general.cache_on_arguments()
    def get_rewards(cls, achievement_id, level):
        """return the new rewards which are given for the achievement level."""

        this_level = DBSession.execute(select([t_rewards.c.id.label("reward_id"),
                                               t_achievements_rewards.c.id,
                                               t_rewards.c.name,
                                               t_achievements_rewards.c.from_level,
                                               t_achievements_rewards.c.value,
                                               t_achievements_rewards.c.value_translation_id],
                                              from_obj=t_rewards.join(t_achievements_rewards))\
                                       .where(and_(or_(t_achievements_rewards.c.from_level <= level,
                                                       t_achievements_rewards.c.from_level == None),
                                                   t_achievements_rewards.c.achievement_id == achievement_id))\
                                       .order_by(t_achievements_rewards.c.from_level))\
                                       .fetchall()

        prev_level = DBSession.execute(select([t_rewards.c.id.label("reward_id"),
                                               t_achievements_rewards.c.id,
                                               t_achievements_rewards.c.value,
                                               t_achievements_rewards.c.value_translation_id],
                                              from_obj=t_rewards.join(t_achievements_rewards))\
                                       .where(and_(or_(t_achievements_rewards.c.from_level <= level-1,
                                                       t_achievements_rewards.c.from_level == None),
                                                   t_achievements_rewards.c.achievement_id == achievement_id))\
                                       .order_by(t_achievements_rewards.c.from_level))\
                                       .fetchall()

        #now compute the diff :-/
        build_hash = lambda x, l: hashlib.md5((str(x["id"])+str(evaluate_string(x["value"], {"level": l}))+str(Translation.trs(x["value_translation_id"], {"level": l}))).encode("UTF-8")).hexdigest()
        prev_hashes = {build_hash(x, level-1) for x in prev_level}
        #this_hashes = {build_hash(x,level) for x in this_level}

        retlist = [x for x in this_level if not build_hash(x, level) in prev_hashes]
        return retlist

    @classmethod
    @cache_general.cache_on_arguments()
    def get_achievement_properties(cls, achievement_id, level):
        """return all properties which are associated to the achievement level."""
        return DBSession.execute(select([t_achievementproperties.c.id.label("property_id"),
                                         t_achievementproperties.c.name,
                                         t_achievementproperties.c.is_variable,
                                         t_achievements_achievementproperties.c.from_level,
                                         t_achievements_achievementproperties.c.value,
                                         t_achievements_achievementproperties.c.value_translation_id],
                                        from_obj=t_achievementproperties.join(t_achievements_achievementproperties))\
                                 .where(and_(or_(t_achievements_achievementproperties.c.from_level <= level,
                                                 t_achievements_achievementproperties.c.from_level == None),
                                             t_achievements_achievementproperties.c.achievement_id == achievement_id))\
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
        return DBSession.execute(t_achievements_rewards.select(t_achievements_rewards.c.id == achievement_reward_id)).fetchone()


class AchievementSubject(ABase):
    """Relation between subjects and achievements, contains level and updated_at date"""
    pass


class GoalEvaluationCache(ABase):
    """Cache for the evaluation of goals for users"""
    pass


class Goal(ABase):
    """A Goal defines a rule on variables that needs to be reached to get achievements"""

    def __unicode__(self, *args, **kwargs):
        if self.name != None:
            name = evaluate_string(self.name, {"level": 1, "goal": '0'})[get_settings().get("fallback_language", "en")]
            return str(name) + " (ID: %s)" % (self.id,)
        else:
            return self.name + " (ID: %s)" % (self.id,)

    @classmethod
    @cache_general.cache_on_arguments()
    def get_goals(cls, achievement_id):
        return DBSession.execute(t_goals.select(t_goals.c.achievement_id == achievement_id)).fetchall()

    @classmethod
    def compute_progress(cls, goal, achievement, subject, evaluation_date):
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

        subject_id = subject["id"]
        timezone = achievement["evaluation_timezone"]

        def generate_statement_cache():
            condition = evaluate_condition(goal["condition"], column_variable=t_variables.c.name.label("variable_name"),
                                                              column_key=t_values.c.key)
            group_by_dateformat = goal["group_by_dateformat"]
            group_by_key = goal["group_by_key"]
            timespan = goal["timespan"]
            maxmin = goal["maxmin"]
            evaluation_type = achievement["evaluation"]
            evaluation_shift = achievement["evaluation_shift"]

            #prepare
            select_cols = [func.sum(t_values.c.value).label("value"),
                           t_values.c.subject_id]

            j = t_values.join(t_variables)

            # We need to access the subject's timezone later
            j = j.join(t_subjects, t_subjects.c.id == t_values.c.subject_id)

            datetime_col = None
            if group_by_dateformat:
                # here we need to convert to users' time zone, as we might need to group by e.g. USER's weekday
                if timezone:
                    datetime_col = func.to_char(text("values.datetime AT TIME ZONE '%s'" % (timezone,)), group_by_dateformat).label("datetime")
                else:
                    datetime_col = func.to_char(text("values.datetime AT TIME ZONE subjects.timezone"), group_by_dateformat).label("datetime")
                select_cols.append(datetime_col)

            if group_by_key:
                select_cols.append(t_values.c.key)

            #build query
            q = select(select_cols,
                       from_obj=j)\
               .where(t_values.c.subject_id == bindparam("subject_id"))\
               .group_by(t_values.c.subject_id)

            if condition is not None:
                q = q.where(condition)

            if timespan:
                #here we can use the utc time
                q = q.where(t_values.c.datetime >= datetime.datetime.utcnow()-datetime.timedelta(days=timespan))

            if evaluation_type != "immediately":
                achievement_date = AchievementDate.compute(
                    evaluation_timezone=timezone,
                    evaluation_type=evaluation_type,
                    evaluation_shift=evaluation_shift,
                    context_datetime=evaluation_date
                )
                if evaluation_type in ('daily', 'weekly', 'monthly', 'yearly'):
                    q = q.where(and_(
                        t_values.c.datetime >= achievement_date.from_date,
                        t_values.c.datetime < achievement_date.to_date
                    ))
                elif evaluation_type == "end":
                    pass
                    #Todo implement for end

            if datetime_col is not None or group_by_key is not False:
                if datetime_col is not None:
                    q = q.group_by(datetime_col)

                if group_by_key is not False:
                    q = q.group_by(t_values.c.key)

                query_with_groups = q.alias()

                select_cols2 = [query_with_groups.c.subject_id]

                if maxmin == "min":
                    select_cols2.append(func.min(query_with_groups.c.value).label("value"))
                else:
                    select_cols2.append(func.max(query_with_groups.c.value).label("value"))

                combined_user_query = select(select_cols2, from_obj=query_with_groups)\
                                      .group_by(query_with_groups.c.subject_id)

                return combined_user_query
            else:
                return q

        #q = cache_goal_statements.get_or_create(str(goal["id"]),generate_statement_cache)
        # TODO: Cache the statement / Make it serializable for caching in redis
        q = generate_statement_cache()

        return DBSession.execute(q, {'subject_id': subject_id})

    @classmethod
    def evaluate(cls, goal, achievement, achievement_date, subject, level, goal_eval_cache_before=False, execute_triggers=True):
        """evaluate the goal for the user_ids and the level"""

        operator = goal["operator"]

        #TODO: Move this call to outer loops
        subject_id = subject["id"]

        subjects_progress = Goal.compute_progress(goal, achievement, subject, achievement_date)
        goal_evaluation = {e["subject_id"]: e["value"] for e in subjects_progress}
        goal_achieved = False

        if goal_eval_cache_before is False:
            goal_eval_cache_before = cls.get_goal_eval_cache(goal["id"], achievement_date, subject_id)

        new = goal_evaluation.get(subject_id, 0.0)

        if goal_eval_cache_before is None or goal_eval_cache_before.get("value", 0.0) != goal_evaluation.get(subject_id, 0.0):

            #Level is the next level, or the current level if I'm alread at max
            params = {
                "level": level
            }
            goal_goal = evaluate_value_expression(goal["goal"], params)
            if goal_goal is not None and operator == "geq" and new >= goal_goal:
                goal_achieved = True
                new = min(new, goal_goal)

            elif goal_goal is not None and operator == "leq" and new <= goal_goal:
                goal_achieved = True
                new = max(new, goal_goal)

            previous_goal = Goal.basic_goal_output(goal, level-1).get("goal_goal",0)
            # Evaluate triggers
            if execute_triggers:
                Goal.select_and_execute_triggers(
                    goal=goal,
                    achievement_date=achievement_date,
                    subject_id=subject_id,
                    level=level,
                    current_goal=goal_goal,
                    previous_goal=previous_goal,
                    value=new
                )

            return Goal.set_goal_eval_cache(goal=goal,
                                            subject_id=subject_id,
                                            achievement_date=achievement_date,
                                            value=new,
                                            achieved = goal_achieved)
        else:
            return Goal.get_goal_eval_cache(goal["id"], achievement_date, subject_id)

    @classmethod
    def select_and_execute_triggers(cls, goal, achievement_date, subject_id, level, current_goal, value, previous_goal):

        if previous_goal == current_goal:
            previous_goal = 0.0

        j = t_achievement_trigger_step_executions.join(t_achievement_trigger_steps)
        executions = {r["goal_trigger_id"]: r["step"] for r in
                      DBSession.execute(
                          select([t_achievement_trigger_steps.c.id.label("step_id"),
                                  t_achievement_trigger_steps.c.goal_trigger_id,
                                  t_achievement_trigger_steps.c.step], from_obj=j).\
                          where(and_(t_achievement_triggers.c.goal_id == goal["id"],
                                     t_achievement_trigger_step_executions.c.achievement_date == achievement_date,
                                     t_achievement_trigger_step_executions.c.subject_id == subject_id,
                                     t_achievement_trigger_step_executions.c.execution_level == level))).fetchall()
                      }

        j = t_achievement_trigger_steps.join(t_achievement_triggers)

        trigger_steps = DBSession.execute(select([
            t_achievement_trigger_steps.c.id,
            t_achievement_trigger_steps.c.goal_trigger_id,
            t_achievement_trigger_steps.c.step,
            t_achievement_trigger_steps.c.condition_type,
            t_achievement_trigger_steps.c.condition_percentage,
            t_achievement_trigger_steps.c.action_type,
            t_achievement_trigger_steps.c.action_translation_id,
            t_achievement_triggers.c.execute_when_complete,
        ], from_obj=j).where(t_achievement_triggers.c.goal_id == goal["id"], )).fetchall()

        trigger_steps = [s for s in trigger_steps if s["step"] > executions.get(s["goal_trigger_id"], -sys.maxsize)]

        exec_queue = {}

        #When editing things here, check the insert_trigger_step_executions_after_step_upsert event listener too!!!!!!!
        if len(trigger_steps) > 0:
            operator = goal["operator"]

            goal_properties = Goal.get_properties(goal, level)

            for step in trigger_steps:
                if step["condition_type"] == "percentage" and step["condition_percentage"]:
                    current_percentage = float(value - previous_goal) / float(current_goal - previous_goal)
                    required_percentage = step["condition_percentage"]
                    if current_percentage >= 1.0 and required_percentage != 1.0 and not step["execute_when_complete"]:
                        # When the user reaches the full goal, and there is a trigger at e.g. 90%, we don't want it to be executed anymore.
                        continue
                    if (operator == "geq" and current_percentage >= required_percentage) \
                        or (operator == "leq" and current_percentage <= required_percentage):
                        if exec_queue.get(step["goal_trigger_id"], {"step": -sys.maxsize})["step"] < step["step"]:
                            exec_queue[step["goal_trigger_id"]] = step

            for step in exec_queue.values():
                current_percentage = float(value - previous_goal) / float(current_goal - previous_goal)
                GoalTriggerStep.execute(
                    trigger_step=step,
                    subject_id=subject_id,
                    current_percentage=current_percentage,
                    value=value,
                    goal_goal=current_goal,
                    goal_level=level,
                    goal_properties=goal_properties,
                    achievement_date=achievement_date
                )


    @classmethod
    def get_goal_eval_cache(cls, goal_id, achievement_date, subject_id):
        """lookup and return cache entry, else return None"""
        v = cache_goal_evaluation.get("%s_%s_%s" % (goal_id, str(achievement_date), subject_id))
        if v:
            return v
        else:
            return None

    @classmethod
    def set_goal_eval_cache(cls, goal, achievement_date, subject_id, value, achieved):
        """set cache entry after evaluation"""
        cache_query = t_evaluations.select().where(and_(t_evaluations.c.goal_id == goal["id"],
                                                        t_evaluations.c.subject_id == subject_id,
                                                        t_evaluations.c.achievement_date == AchievementDate.db_format(achievement_date)))
        cache = DBSession.execute(cache_query).fetchone()

        if not cache:
            q = t_evaluations.insert()\
                                       .values({"subject_id": subject_id,
                                                "goal_id": goal["id"],
                                                "value": value,
                                                "achieved": achieved,
                                                "achievement_date": AchievementDate.db_format(achievement_date)})
            update_connection().execute(q)
        elif cache["value"] != value or cache["achieved"] != achieved:
            #update
            q = t_evaluations.update()\
                                       .where(and_(t_evaluations.c.goal_id == goal["id"],
                                                   t_evaluations.c.subject_id == subject_id,
                                                   t_evaluations.c.achievement_date == AchievementDate.db_format(achievement_date)))\
                                       .values({"value": value,
                                                "achieved": achieved,
                                                "achievement_date": AchievementDate.db_format(achievement_date)})
            update_connection().execute(q)

        data = {
            "id": goal["id"],
            "value": value,
            "achieved": achieved,
            "goal": goal["goal"],
            "name": goal["name"],
            "achievement_id": goal["achievement_id"],
            "priority": goal["priority"]
        }

        achievement_id = goal["achievement_id"]
        achievement = Achievement.get_achievement(achievement_id)

        level = min((Achievement.get_level_int(subject_id, achievement["id"], achievement_date) or 0) + 1, achievement["maxlevel"])

        goal_output = Goal.basic_goal_output(data, level)

        goal_output.update({
            "achieved": achieved,
            "value": value,
        })

        cache_goal_evaluation.set("%s_%s_%s" % (goal["id"], str(achievement_date), subject_id), goal_output)

        return goal_output

    @classmethod
    def clear_subject_goal_caches(cls, subject_id, goal_ids_with_achievement_date):
        """clear the evaluation cache for the user and gaols"""
        for goal_id, achievement_date in goal_ids_with_achievement_date:
            cache_goal_evaluation.delete("%s_%s_%s" % (goal_id, str(achievement_date), subject_id))
            s = update_connection()
            s.execute(t_evaluations.delete().where(
                and_(t_evaluations.c.subject_id == subject_id,
                     t_evaluations.c.goal_id == goal_id,
                     t_evaluations.c.achievement_date == AchievementDate.db_format(achievement_date)))
            )

    @classmethod
    def get_leaderboard(cls, goal, achievement_date, subject_ids):
        """get the leaderboard for the goal and userids"""

        q = select([t_evaluations.c.subject_id,
                    t_evaluations.c.value])\
                .where(and_(t_evaluations.c.subject_id.in_(subject_ids),
                            t_evaluations.c.goal_id == goal["id"],
                            t_evaluations.c.achievement_date == AchievementDate.db_format(achievement_date),
                            ))\
                .order_by(t_evaluations.c.value.desc(),
                          t_evaluations.c.subject_id.desc())
        items = DBSession.execute(q).fetchall()

        subjects = Subject.get_subjects(subject_ids)

        requested_subject_ids = set(int(s) for s in subject_ids)
        values_found_for_subject_ids = set([int(x["subject_id"]) for x in items])
        missing_subject_ids = requested_subject_ids - values_found_for_subject_ids
        missing_subjects = Subject.get_subjects(missing_subject_ids).values()
        if len(missing_subjects)>0:
            #the goal has not been evaluated for some subjects...
            achievement = Achievement.get_achievement(goal["achievement_id"])

            for subject in missing_subjects:
                subject_has_level = Achievement.get_level_int(subject["id"], achievement["id"], achievement_date)
                subject_wants_level = min((subject_has_level or 0)+1, achievement["maxlevel"])

                Goal.evaluate(goal, achievement, achievement_date, subject, subject_wants_level)

            #rerun the query
            items = DBSession.execute(q).fetchall()

        positions = [{"subject": Subject.basic_output(subjects[items[i]["subject_id"]]),
                      "value": items[i]["value"],
                      "position": i} for i in range(0, len(items))]

        return positions

    @classmethod
    @cache_general.cache_on_arguments()
    def get_goal_properties(cls, goal_id, level):
        """return all properties which are associated to the achievement level."""

        #NOT CACHED, as full-basic_output is cached (see Goal.basic_output)

        return DBSession.execute(select([t_goalproperties.c.id.label("property_id"),
                                         t_goalproperties.c.name,
                                         t_goals_goalproperties.c.from_level,
                                         t_goals_goalproperties.c.value,
                                         t_goals_goalproperties.c.value_translation_id],
                                        from_obj=t_goalproperties.join(t_goals_goalproperties))\
                                 .where(and_(or_(t_goals_goalproperties.c.from_level <= level,
                                                 t_goals_goalproperties.c.from_level == None),
                                             t_goals_goalproperties.c.goal_id == goal_id))\
                                 .order_by(t_goals_goalproperties.c.from_level))\
                        .fetchall()

    @classmethod
    @cache_general.cache_on_arguments()
    def basic_goal_output(cls, goal, level):
        goal_goal = evaluate_value_expression(goal["goal"], {"level": level})
        properties = {
            str(r["property_id"]): {
                "property_id": r["property_id"],
                "name": r["name"],
                "value": evaluate_string(r["value"], {"level": level}),
                "value_translated": Translation.trs(r["value_translation_id"], {"level": level}),
            } for r in Goal.get_goal_properties(goal["id"], level)
        }
        return {
            "goal_id": goal["id"],
            "goal_name": evaluate_string(goal["name"], {"level": level, "goal": goal_goal}),
            "goal_goal": goal_goal,
            "priority": goal["priority"],
            "properties": properties,
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
    def trs(cls, translation_id, params={}):
        """returns a map of translations for the translation_id for ALL languages"""

        if translation_id is None:
            return None
        try:
            # TODO support params which are results of this function itself (dicts of lang -> value)
            # maybe even better: add possibility to refer to other translationvariables directly (so they can be modified later on)
            ret = {str(x["name"]): evaluate_string(x["text"], params) for x in cls.get_translation_variable(translation_id)}
        except Exception as e:
            ret = {str(x["name"]): x["text"] for x in cls.get_translation_variable(translation_id)}
            log.exception("Evaluation of string-forumlar failed: %s" % (ret.get(get_settings().get("fallback_language", "en"), translation_id),))
            
        if not get_settings().get("fallback_language", "en") in ret:
            ret[get_settings().get("fallback_language", "en")] = "[not_translated]_"+str(translation_id)
        
        for lang in cls.get_languages():
            if not str(lang["name"]) in ret:
                ret[str(lang["name"])] = ret[get_settings().get("fallback_language", "en")]
        
        return ret    
    
    @classmethod
    @cache_translations.cache_on_arguments()
    def get_translation_variable(cls, translation_id):
        return DBSession.execute(select([t_translations.c.text,
                                  t_languages.c.name],
                              from_obj=t_translationvariables.join(t_translations).join(t_languages))\
                       .where(t_translationvariables.c.id == translation_id)).fetchall()
    
    @classmethod
    @cache_translations.cache_on_arguments()                   
    def get_languages(cls):
        return DBSession.execute(t_languages.select()).fetchall()


class SubjectMessage(ABase):
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
        text = SubjectMessage.get_text(message)
        language = get_settings().get("fallback_language", "en")
        j = t_subjects.join(t_languages)
        subject_language = DBSession.execute(select([t_languages.c.name], from_obj=j).where(t_subjects.c.id == message["subject_id"])).fetchone()
        if subject_language:
            language = subject_language["name"]
        translated_text = text[language]

        if not message["has_been_pushed"]:
            try:
                send_push_message(
                    user_id=message["subject_id"],
                    text=translated_text,
                    custom_payload={},
                    title=get_settings().get("push_title", "Gamification-Engine")
                )
            except Exception as e:
                log.error(e, exc_info=True)
            else:
                DBSession.execute(t_subject_messages.update().values({"has_been_pushed": True}).where(t_subject_messages.c.id == message["id"]))

class GoalTrigger(ABase):
    def __unicode__(self, *args, **kwargs):
        return "GoalTrigger: %s" % (self.id,)

class GoalTriggerStep(ABase):
    def __unicode__(self, *args, **kwargs):
        return "GoalTriggerStep: %s" % (self.id,)

    @classmethod
    def execute(cls, trigger_step, subject_id, current_percentage, value, goal_goal, goal_level, goal_properties, achievement_date, suppress_actions=False):
        uS = update_connection()
        uS.execute(t_achievement_trigger_step_executions.insert().values({
            'subject_id': subject_id,
            'trigger_step_id': trigger_step["id"],
            'execution_level': goal_level,
            'achievement_date': AchievementDate.db_format(achievement_date)
        }))
        if not suppress_actions:
            if trigger_step["action_type"] == "subject_message":
                m = SubjectMessage(
                    subject_id=subject_id,
                    translation_id=trigger_step["action_translation_id"],
                    params=dict({
                        'value': value,
                        'goal': goal_goal,
                        'percentage': current_percentage
                    },**goal_properties),
                    is_read=False,
                    has_been_pushed=False
                )
                uS.add(m)


class Task(ABase):
    def __unicode__(self, *args, **kwargs):
        return "Task: %s" % (self.id,)


class TaskExecution(ABase):
    def __unicode__(self, *args, **kwargs):
        return "TaskExecution: %s" % (self.id,)


@event.listens_for(GoalTriggerStep, "after_insert")
@event.listens_for(GoalTriggerStep, 'after_update')
def insert_trigger_step_executions_after_step_upsert(mapper,connection,target):
    """When we create a new Trigger-Step, we must ensure, that is will not be executed for the users who already met the conditions before."""

    subject_ids = [x["id"] for x in DBSession.execute(select([t_subjects.c.id, ], from_obj=t_subjects)).fetchall()]
    subjects = Subject.get_subjects(subject_ids).values()
    goal = target.trigger.goal
    achievement = goal.achievement

    for subject in subjects:
        achievement_date = AchievementDate.compute(
            evaluation_timezone=achievement["evaluation_timezone"],
            evaluation_type=achievement["evaluation"],
            evaluation_shift=achievement["evaluation_shift"]
        )

        subject_has_level = Achievement.get_level_int(subject["id"], achievement["id"], achievement_date)
        subject_wants_level = min((subject_has_level or 0) + 1, achievement["maxlevel"])
        goal_eval = Goal.evaluate(goal, achievement, achievement_date, subject, subject_wants_level, None, execute_triggers=False)

        previous_goal = Goal.basic_goal_output(goal, subject_wants_level - 1).get("goal_goal", 0)
        if previous_goal == goal_eval["goal_goal"]:
            previous_goal = 0.0

        current_percentage = float(goal_eval["value"]-previous_goal) / float(goal_eval["goal_goal"]-previous_goal)
        operator = goal["operator"]
        required_percentage = target["condition_percentage"]

        if (operator == "geq" and current_percentage >= required_percentage) \
                or (operator == "leq" and current_percentage <= required_percentage):
            GoalTriggerStep.execute(
                trigger_step=target,
                subject_id=subject["id"],
                current_percentage=current_percentage,
                value=goal_eval["value"],
                goal_goal=goal_eval["goal_goal"],
                goal_level=subject_wants_level,
                goal_properties=Goal.get_properties(goal,subject_wants_level),
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
    'roles': relationship(AuthRole, secondary=t_auth_users_roles, backref="users"),
    'subject': relationship(Subject, backref="auth_users")
})

mapper(AuthToken, t_auth_tokens, properties={
    'user': relationship(AuthUser, backref="tokens")
})

mapper(AuthRole, t_auth_roles, properties={

})

mapper(AuthRolePermission, t_auth_roles_permissions, properties={
    'role': relationship(AuthRole, backref="permissions"),
})

mapper(Subject, t_subjects, properties={
    'friends': relationship(Subject, secondary=t_subjectrelations,
                            primaryjoin=t_subjects.c.id == t_subjectrelations.c.from_id,
                            secondaryjoin=t_subjects.c.id == t_subjectrelations.c.to_id),
    'language': relationship(Language, backref="subjects"),
    'type': relationship(SubjectType, backref="subjects"),
    'subsubjects': relationship(Subject, secondary=t_subjects_subjects,
                                       primaryjoin=t_subjects.c.id==t_subjects_subjects.c.part_of_id,
                                       secondaryjoin=t_subjects.c.id==t_subjects_subjects.c.subject_id,
                                       backref="part_of_subjects"),
})

mapper(SubjectType, t_subjecttypes, properties={
    'subtypes': relationship(SubjectType, secondary=t_subjecttypes_subjecttypes,
                             primaryjoin=t_subjecttypes.c.id == t_subjecttypes_subjecttypes.c.part_of_id,
                             secondaryjoin=t_subjecttypes.c.id == t_subjecttypes_subjecttypes.c.subjecttype_id,
                             backref="part_of_types"),
})

mapper(SubjectDevice, t_subject_device, properties={
    'subject': relationship(Subject, backref="devices"),
})

mapper(Variable, t_variables, properties={
   'values': relationship(Value),
})

mapper(Value, t_values, properties={
   'subject': relationship(Subject, primaryjoin=t_values.c.subject_id == t_subjects.c.id),
   'agent': relationship(Subject, primaryjoin=t_values.c.agent_id == t_subjects.c.id),
   'variable': relationship(Variable)
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
   'subjects': relationship(AchievementSubject, backref='achievement'),
   'properties': relationship(AchievementAchievementProperty, backref='achievement'),
   'rewards': relationship(AchievementReward, backref='achievement'),
   'goals': relationship(Goal, backref='achievement'),
   'achievementcategory': relationship(AchievementCategory, backref='achievements'),
   'player_subjecttype': relationship(SubjectType, primaryjoin=t_achievements.c.player_subjecttype_id == t_subjecttypes.c.id),
   'context_subjecttype': relationship(SubjectType, primaryjoin=t_achievements.c.context_subjecttype_id == t_subjecttypes.c.id),
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
mapper(AchievementSubject, t_achievements_subjects)

mapper(Goal, t_goals, properties={

})
mapper(GoalProperty, t_goalproperties)
mapper(GoalGoalProperty, t_goals_goalproperties, properties={
   'property' : relationship(GoalProperty, backref='goals'),
   'value_translation' : relationship(TranslationVariable),
   'goal' : relationship(Goal, backref='properties',),
})
mapper(GoalEvaluationCache, t_evaluations, properties={
   'subject': relationship(Subject),
   'goal': relationship(Goal)
})

mapper(GoalTrigger, t_achievement_triggers, properties={
    'goal': relationship(Goal, backref="triggers"),
})
mapper(GoalTriggerStep, t_achievement_trigger_steps, properties={
    'trigger': relationship(GoalTrigger,backref="steps"),
    'action_translation': relationship(TranslationVariable)
})

mapper(Language, t_languages)
mapper(TranslationVariable, t_translationvariables)
mapper(Translation, t_translations, properties={
   'language': relationship(Language),
   'translationvariable': relationship(TranslationVariable, backref="translations"),
})

mapper(SubjectMessage, t_subject_messages, properties = {
    'subject': relationship(Subject, backref="subject_messages"),
    'translationvariable': relationship(TranslationVariable),
})

mapper(Task, t_tasks, properties={

})

mapper(TaskExecution, t_taskexecutions, properties={
    'task': relationship(Task, backref="executions"),
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
