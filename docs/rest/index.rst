:title: rest
:description: introduction to the REST api 

REST API
--------

Add or update user data
=======================

   - POST to "/add_or_update_user/{userId}" 
      - URL parameters:
         - userId (the Id of a user in your system)
      - POST parameters:
         - lat (float latitude)
         - lon (float longitude)
         - country (String country)
         - city (String city)
         - region (String city)
         - friends (comma separated list of user Ids)
         
   - add or updates a user with Id {userId} and Post parameters into the engines database
   - if friends Ids are not registered a empty record with only the user Id will be created

   
Delete a user
=============

   - DELETE to "/delete_user/{userId}"


Increase Value
==============
   
   - POST to "/increase_value/{variable_name}/{userId}"
      - URL parameters:
         - variable_name (the name of the variable to increase or decrease)
         - userId (the Id of the user)
	  - POST parameters:
		 - value (the increase/decrease value in Double)
	
   - if the userId is not registered a empty record with only the userId will be created
   - directly evaluates all goals associated with this variable_name
   - directly returns new reached achievements


Get Progress
============

   - get complete achievement progress for a single user

   - GET to "/progress/{userId}"

   - returns the complete achievement progress of a single user

Get a single achievement Level
==============================

   - GET to "/increase_value/{variable_name}/{userId}"

   - can be used to check if a user is allowed to use a reward