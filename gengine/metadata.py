from sqlalchemy.orm.session import Session, sessionmaker
import transaction
from sqlalchemy.orm.scoping import scoped_session
from zope.sqlalchemy.datamanager import ZopeTransactionExtension
from sqlalchemy.ext.declarative.api import declarative_base

class MySession(Session):
    """This allow us to use the flask-admin sqla extension, which uses DBSession.commit() rather than transaction.commit()"""
    def commit(self,*args,**kw):
        transaction.commit(*args,**kw)
        
    def rollback(self,*args,**kw):
        transaction.abort(*args,**kw)

DBSession=None

def init_session(override_session=None):
    global DBSession
    if override_session:
        DBSession = override_session
    else:
        DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension(), class_=MySession)) 

Base=None

def init_declarative_base(override_base=None):
    global Base
    if override_base:
        Base=override_base
    else:
        Base = declarative_base()
        
def init_db(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    
    