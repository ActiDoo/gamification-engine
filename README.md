# gamification-engine

gamification-engine (gengine) is an open source software (AGPL) for integrating any kinds of gamification features into your product.

## Features

- multi level achievements
- multi goal achievements
- progress and single goals 
- leader boards / ladder
- achievements can be reached directly, daily, weekly, monthly or yearly
- time zone independent (correct daily, weekly.. evaluations among time zones)
- social dependencies (e.g. each the highest score among your friends)
- localized achievements (e.g. reach the highest score among all users in Germany)
- custom definable rules and strings
- custom definable achievement properties and rewards
- custom definable languages and translations
- dependencies between achievements (prerequisites & postconditions)
- high performance / scalable
- administrative fronted

## Rest-Interface

simple rest-interface to communicate with arbitrary Systems


- Register / Add a new user

	- POST to "/add_or_update_user/{userId}" 
		- Get fields:
			- userId (the Id of a user in your system)
		- Body fields:
			- lat (float latitude)
			- lon (float longitude)
			- country (String country)
			- city (String city)
			- region (String city)
			- friends (comma separated list of user Ids)
			
	- add or updates a user with Id {userId} and Post parameters into the engines database
	- if friends Ids are not registered a empty record with only the user Id will be created

	
- Delete an registered user

	- DELETE to "/delete_user/{userId}"

	
- Increase / Decrease a progress variable for a single user

	- GET to "/increase_value/{variable_name}/{userId}"
		- Get fields:
			- variable_name (the name of the variable to increase or decrease)
			- userId (the Id of the user)

	- if the userId is not registered a empty record with only the user Id will be created
	- directly evaluates all goals associated with this variable_name
	- directly returns new reached achievements

	
- get complete achievement progress for a single user

	- GET to "/progress/{userId}"

	- returns the complete achievement progress of a single user


- Get a single achievement Level

	- GET to "/increase_value/{variable_name}/{userId}"

	- can be used to check if a user is allowed to use a reward

## Roadmap
see http://gamification-engine.readthedocs.org/en/latest/

## Who are you ?
We developed the gamification engine for ActiDoo (www.actidoo.com) and extracted the component to release it to the open source community.
We offer commercial support at www.gamification-software.com

## AGPL ?
You may use the engine in commercial products, but you need to contribute all your modifications and improvements back to the community.
