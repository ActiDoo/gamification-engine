:title: gamification-engine installation
:description: installing the gamification-engine

Installation
------------

The gamification-engine is available as a python package.
You can install it by invoking

.. highlight:: bash

::

    $ pip install gamification-engine
    $ gengine_quickstart mygengine
    $ cd mygengine

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
