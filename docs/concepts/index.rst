:title: concepts
:description: introduction to the basic concepts 

Concepts
--------

Assumption: You installed the gamification-engine and can open the admin interface at /admin/

Users
=========

In order to register a new user inside the engine you have to perform a REST-POST to "/add_or_update_user/{userId}"

following properties can be set:
.. lat
.. lon
.. country
.. city
.. region
.. friends

Variables
=========

variables define different progresses for achievements based on users
e.g. a variable user_chatmessages can be used to count the chat messages a user has send

in order to increase or decrease a variable you have to perform the REST-GET to "/increase_value/{variable_name}/{user_id}"

if the user_id is unknown a new one will be created

Values / Events
===============

Goals
=====

Achievements
============


Properties
==========


Rewards
=======
