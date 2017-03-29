:title: concepts
:description: introduction to the basic concepts 

Concepts
--------

Assumption: You installed the gamification-engine and you can open the admin interface at /admin/

Users
=====

Gamification is always about users.
As the gamification-engine include location-based, time-based and social features, it needs to know some information about the user:

 - lat
 - lon
 - country
 - city
 - region
 - friends
 - groups

Variables / Values / Events
===========================

Variables describe events that can happen in your application.
 
When such an event occurs, your application triggers the gamification engine to increase the value of the variable for the relevant users.

The storage of these values can be grouped by day, month or year to save storage.
Note that if you want to specify time-based rules like "event X occurs Y times in the last 14 days", you may not group the values by month or year.

In addition to integers, the application can also add additional keys to the variables to model application-specific data.

Goals
=====

Goals define conditions that need to be fulfilled in order to get an achievement.

 - goal:                the value that is used for comparison
 - operator:            "geq" or "leq"; used for comparison
 - condition:           the rule in json format, see below
 - group_by_dateformat: passed as a parameter to to_char ( PostgreSQL-Docs_ )
                        e.g. you can select and group by the weekday by using "ID" for ISO 8601 day of the week (1-7) which can afterwards be used in the condition
 - group_by_key:        group by the key of the values table
 - timespan:            number of days which are considered (uses utc, i.e. days*24hours)
 - maxmin:              "max" or "min" - select min or max value after grouping

.. _PostgreSQL-Docs: http://www.postgresql.org/docs/9.3/static/functions-formatting.html
 
The conditions contain a python expression that must evaluate to a valid parameter for SQLAlchemy's where function. 

### Examples:

When the user has participated in the seminars 5, 7, and 9, he should get an achievement.
We first need to create a variable "participate" and tell our application to increase the value of that variable with the seminar ID as key for the user by 1.
The constraint that a user may not attend multiple times to one seminar is covered by the application and not discussed here.
In the gamification-engine we create a Goal with the following formular:

.. code:: json

   {
     "term": {
       "type": "literal",
       "variable": "participate",
       "key": ["5","7","9"],
       "key_operator": "IN"
     }
   }
   
Whenever a value for "participate" is set, this Goal is evaluated. 
It sums up all rows with the given condition and compares it to the Goal's "goal" attribute using the given operator.


Another simple example is to count the number of invited users.
After inviting 30 other users to the application, the user should get an achievement.
We create a variable "invite_users" and set the condition as follows:

.. code:: python

   p.var=="invite_users"
   {
     "term": {
       "type": "literal",
       "variable": "invite_users"
     }
   }
   
Furthermore we set the Goal's goal to 30 and the operator to "geq".

 

If you want to make use of Goals with multiple levels, you probably want to increase the goal attribute with every level.
Therefore, you can mathematical formulas.

Example:

For the first level, the user needs to invite 5 other users, for the second level 10 other users and so on.

.. code:: python
   
   5*level # level is set by the gamification engine

For further information about the rule language, we currently need to refer to the sources_ .

.. _sources: https://github.com/ActiDoo/gamification-engine/blob/develop/gengine/app/formular.py

Achievements
============

Achievements contain a collection of rewards that are given to users who reach all assigned Goals of the Achievement.
To allow multiple levels, you can set the *maxlevel* attribute.

You can specify time-based constraints by setting *valid_start* and *valid_end*,
and location-based constraints by setting *lat*,*lng* and *max_distance*.

The *hidden* flag can be used to model secret achievements. The *priority* specifies a custom order in output lists.

Achievements can also be used to model leaderboards.
Therefor you need to assign a single Goal whose *goal attribute* is set to None.
The Achievement's *relevance* attribute specifies in which context the leaderboard should be computed.
Valid values are "friends", "city" and "own".

For setting up recurring achievements, set the *evaluation* to e.g. *monthly*. The *evaluation_timezone* parameter specifies when exactly the periods begin and end.

There is a *view_permission* setting that can be used when authorization is active. It specifies whether other users can see the goal progress.

Properties
==========
A property describes an Achievement or a Goal of our system, like the name, image, description or XP the user should get. 
The Values of Properties can again be python formulas.
Inside the formula you can make use of the level by using *level*.
    
Additionally, Properties can be used as Variables.
This is useful to model goals like "reach 1000xp".


Rewards
=======
From the model perspective Rewards are similar to Properties.
The main difference occurs during the evaluation of Achievements, more specifically when a user reaches a new level.
While the formulas for the properties are simply evaluated for the specific level,
the evaluated formulas of the rewards are compared to lower levels.

The engine thus knows for each achieved level, which reward is new and can tell the application about this.
In your application this could for example trigger a badge notification.


Further new concepts
=======
Since the latest version, some complete new optional concepts and features are added to the gamification-engine:

 - Authentication
 - Push Notifications
 - Messages
 
All of these features are optional and they are not required to successfully use the engine. For the moment we refer to the source code and the description of the Rest API, a detailed documentation will follow.
