import os

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
    'alembic'
    ]

setup(name='gamification-engine',
      version='0.1.31',
      description='The Gamification-Engine (gengine) provides an API for integrating any kinds of gamification features.',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License"
        ],
      author='Marcel Sander, Jens Janiuk',
      author_email='marcel@gamification-software.com',
      license='MIT',
      url='https://www.gamification-software.com',
      keywords='web wsgi bfg pylons pyramid gamification',
      packages=find_packages()+["gengine_quickstart_template",],
      include_package_data=True,
      zip_safe=False,
      test_suite='gengine',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = gengine:main
      [console_scripts]
      initialize_gengine_db = gengine.scripts.initializedb:main
      gengine_quickstart = gengine.scripts.quickstart:main
      """,
     )
