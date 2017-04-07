:title: gamification-engine installation
:description: installing the gamification-engine

Upgrading
------------

From 0.1 to 0.2
============

In version 0.2 we have introduced **breaking changes** that make it impossible to do an automatic upgrade. If you are happy with 0.1, there is no need to upgrade. Furthermore, we have switched to Python 3.x as our main target environment.
For performing a manual upgrade the following steps are required:

 - Install a new instance of 0.2
 - Recreate all settings / achievements manually using the new goal condition syntax
 - Recreate users
 - Copy values data

*For future updates we will try to keep the goal condition syntax backwards compatible.*
