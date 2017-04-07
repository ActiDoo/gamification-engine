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
         - groups (comma separated list of group Ids)
         - language (name)
         - additional_public_data (JSON)
         
   - add or updates a user with Id {userId} and Post parameters into the engines database
   - if friends Ids are not registered a empty record with only the user Id will be created

   
Delete a user
=============

   - DELETE to "/delete_user/{userId}"


Increase Value
==============
   
   - POST to "/increase_value/{variable_name}/{userId}/{key}"
      - URL parameters:
         - variable_name (the name of the variable to increase or decrease)
         - userId (the Id of the user)
         - key (an optional key, describing the context of the event, can be used in rules)
      - POST parameters:
         - value (the increase/decrease value in Double)
	
   - if the userId is not registered an error will be thrown
   - directly evaluates all goals associated with this variable_name
   - directly returns new reached achievements

Increase multiple Values at once
==============
   
   - POST to "/increase_multi_values"
      - JSON request body:
           .. code:: json
           {
               "{userId}" : {
                   "{variable}" : [
                       {
                           "key" : "{key}",
                           "value" : "{value}"
                       }
                   ]
               }
           }
    
    - directly evaluates all goals associated with the given variables
    - directly returns new reached achievements
   
Get Progress
============

   - get complete achievement progress for a single user

   - GET to "/progress/{userId}"

   - returns the complete achievement progress of a single user

Get a single achievement Level
==============================

   - GET to "/achievement/{achievement_id}/level/{level}"

   - retrieves information about the rewards/properties of an achievement level

Authentication
==============================
   - POST to "/auth/login"
   - Parameters in JSON-Body: email, password
   - Returns a json body with a token:
        .. code:: json
        {
            "token" : "foobar...."
        }

Register Device (for Push-Messages)
==============================
   - POST to "/register_device/{user_id}"
   - Parameters in JSON-Body: device_id, push_id, device_os, app_version
   - Returns a json body with an ok status, or an error:
        .. code:: json
        {
            "status" : "ok"
        }

Get Messages
==============================
   - GET to "/messages/{user_id}"
   - Possible GET Parameters: offset
   - Limit is always 100
   - Returns a json body with the messages:
        .. code:: json
        {
            "messages" : [{
                "id" : "....",
                "text" : "....",
                "is_read" : false,
                "created_at" : "...."
            }]
        }

Set Messages Read
==============================
   - POST to "/read_messages/{user_id}"
   - Parameters in JSON-Body: message_id
   - Sets all messages as read which are at least as old, as the given message
   - Returns a json body with an ok status, or an error:
        .. code:: json
        {
            "status" : "ok"
        }

