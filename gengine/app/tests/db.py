import os

import logging
log = logging.getLogger(__name__)

try:
    import testing.postgresql
except ImportError as e:
    log.info("testing.postgresql not installed")

db = None

def setupDB():
    # Generate Postgresql class which shares the generated database
    global db
    db = testing.postgresql.PostgresqlFactory(
        postgres=os.environ.get("TEST_POSTGRES",None),
        initdb=os.environ.get("TEST_INITDB",None),
        cache_initialized_db=True
    )

def unsetupDB():
    # clear cached database at end of tests
    global db
    db.clear_cache()
