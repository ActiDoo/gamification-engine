:title: gamification-engine installation
:description: installing the gamification-engine

Installation
------------

Requirements
============

The gamification-engine requires an installed python distribution in version 3.x. It uses several language structures which are not supported in Python 2.x. Furthermore, the only currently supported persistence layer is PostgreSQL. Also the corresponding development packages are required (for Ubuntu/Debian: libpq-dev and python3-dev).


Installation from PyPI
======================

The gamification-engine is available as a python package.
You can install it by invoking

.. highlight:: bash

::

    $ pip install gamification-engine
    $ gengine_quickstart mygengine
    $ cd mygengine

In the latest version, there are some optional dependencies for auth pushes and testing. To use these features install it in the following way:

.. highlight:: bash

::

    $ pip install gamification-engine[auth,pushes,testing]

Afterwards edit production.ini according to your needs.

Database
========

The only currently supported persistence layer is PostgreSQL as we make use of its timezone-related features.

To create the tables run:

.. highlight:: bash

::

    $ initialize_gengine_db production.ini

Caching
=======

For caching we make use of two different approaches:
    - using dogpile.cache_ for caching database lookups and computations
    - using memcached_ as a URL-based cache that can be served directly by nginx_

The second approach is optional but highly recommended, it can be deactivated by setting urlcache_active = false in your ini-file.

.. _dogpile.cache: https://dogpilecache.readthedocs.org/
.. _memcached: http://memcached.org/
.. _nginx: http://nginx.org/

Serving
=======

You can use any WSGI-supporting webserver.
(e.g. nginx as a reverse-proxy to uwsgi)

To quickly get started, you can run: 

.. highlight:: bash

::

   $ pserve production.ini

Heroku-style
============

There is also an Heroku-like Project (we use dokku) at gamification-engine-dokku_

.. _gamification-engine-dokku: https://github.com/ActiDoo/gamification-engine-dokku


Commercial Support
==================

Commercial support is available at https://www.gamification-software.com or together with app development at https://www.appnadoo.de
