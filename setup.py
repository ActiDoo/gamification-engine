import os
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'pytz',
    'dogpile.cache',
    'pyramid_dogpile_cache',
    'Flask>=0.10.1',
    'flask-admin',
    'psycopg2',
    'pymemcache',
    'mock',
    'alembic',
    'raven',
    'jsl',
    'jsonschema',
    'pyparsing',
    'python-crontab',
    'croniter',
    'zope.interface',
    'zope.sqlalchemy',
    'argon2'
]

version = ''
with open('gengine/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')
	
setup(name='gamification-engine',
      version=version,
      description='The Gamification-Engine (gengine) provides an API for integrating any kinds of gamification features.',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License"
        ],
      author='Marcel Sander, Jens Janiuk, Matthias Feldotto',
      author_email='marcel@gamification-software.com',
      license='MIT',
      url='https://www.gamification-software.com',
      keywords='web wsgi bfg pylons pyramid gamification',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='gengine',
      install_requires=requires,
      extras_require={
        "auth": [
            'argon2'
        ],
        "pushes": [
            'tapns3',
            'python-gcm',
        ],
        "testing": [
            'testing.postgresql',
            'testing.redis',
            'names'
        ]
      },
      entry_points="""\
      [paste.app_factory]
      main = gengine:main
      [console_scripts]
      initialize_gengine_db = gengine.maintenance.scripts.initializedb:main
      generate_gengine_erd = gengine.maintenance.scripts.generate_erd:main
      generate_gengine_revision = gengine.maintenance.scripts.generate_revision:main
      gengine_push_messages = gengine.maintenance.scripts.push_messages:main
      gengine_scheduler_beat = gengine.maintenance.scripts.scheduler_beat:main
      gengine_scheduler_worker = gengine.maintenance.scripts.scheduler_worker:main
      [redgalaxy.plugins]
      gengine = gengine:redgalaxy
      """,
     )
