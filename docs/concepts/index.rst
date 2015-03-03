:title: concepts
:description: introduction to the basic concepts 

Concepts
--------

Assumption: You installed the gamification-engine and can open the admin interface at /admin/

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

Variables / Values / Events
===========================

Variables describe events that can happen in your application.
 
When such an event occurs, your application triggers the gamification engine to increase the value of the variable for the relevant users.

The storage of these values can be grouped by day, month or year to save storage.
Note that if you want to specify time-based rules like "event X occurs Y times in the last 14 days", you may not group the values by month or year.

In addition to integers, the application can also set keys to model application-specific data.

Goals
=====

Goals define conditions that need to be fulfilled in order to get an achievement.

 - goal:                the value that is used for comparison
 - operator:            "geq" or "leq"; used for comparison
 - condition:           the rule as python code, see below
 - group_by_dateformat: passed as a parameter to to_char ( http://www.postgresql.org/docs/9.3/static/functions-formatting.html )
                        e.g. you can select and group by the weekday by using "ID" for ISO 8601 day of the week (1-7) which can afterwards be used in the condition
 - group_by_key:        group by the key of the values table
 - timespan:            number of days which are considered (uses utc, i.e. days*24hours)
 - maxmin:              "max" or "min" - select min or max value after grouping
 - evaluation:          "daily", "weekly", "monthly", "yearly" evaluation (users timezone)
 
The conditions contain a python expression that must evaluate to a valid parameter for SQLAlchemy's where function. 

Examples:

When the user has participated in the seminars 5, 7, and 9, he should get an achievement.
We first need to create a variable "participate" and tell our application to increase the value of that variable with the seminar ID as key for the user by 1.
The constraint that a user may not attend multiple times to one seminar is covered by the application and not discussed here.
In the gamification-engine we create a Goal with the following formular:

.. code:: python
   and_(p.var=="participate", p.key.in_(["5","7","9"]))
   
Whenever a value for "participate" is set, this Goal is evaluated. 
It sums up all rows with the given condition and compares it to the Goal's "goal" attribute using the given operator.


Another simple example is to count the number of invited users.
After inviting 30 other users to the application, the user should get an achievement.
We create a variable "invite_users" and set the condition as follows:

.. code:: python
   p.var=="invite_users"
   
Furthermore we set the Goal's goal to 30 and the operator to "geq".

Achievements
============



Properties
==========


Rewards
=======
