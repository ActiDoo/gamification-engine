import testing.postgresql

db = None

def setupDB():
    # Generate Postgresql class which shares the generated database
    global db
    db = testing.postgresql.PostgresqlFactory(cache_initialized_db=True)

def unsetupDB():
    # clear cached database at end of tests
    global db
    db.clear_cache()
