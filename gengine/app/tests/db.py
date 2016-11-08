import testing.postgresql
import os

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
