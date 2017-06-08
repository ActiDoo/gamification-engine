from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session, sessionmaker
import transaction
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.sql.schema import MetaData
from zope.sqlalchemy.datamanager import ZopeTransactionExtension
from sqlalchemy.ext.declarative.api import declarative_base

from gengine.base.util import Proxy, dt_now


class LimitingQuery(Query):

    def get(self, ident):
        # override get() so that the flag is always checked in the
        # DB as opposed to pulling from the identity map. - this is optional.
        return Query.get(self.populate_existing(), ident)

    def __iter__(self):
        return Query.__iter__(self.private())

    def from_self(self, *ent):
        # override from_self() to automatically apply
        # the criterion too.   this works with count() and
        # others.
        return Query.from_self(self.private(), *ent)

    def private(self):
        mzero = self._mapper_zero()
        if mzero is not None:
            crit = mzero.class_.deleted_at == None
            return self.enable_assertions(False).filter(crit)
        else:
            return self


class MySession(Session):
    """This allow us to use the flask-admin sqla extension, which uses DBSession.commit() rather than transaction.commit()"""
    def commit(self,*args,**kw):
        transaction.commit(*args,**kw)

    def rollback(self, *args, **kw):
        transaction.abort(*args,**kw)

    def delete(self, model):
        if hasattr(model, "deleted_at"):
            model.deleted_at = dt_now()
            self.add(model)
            self.flush()
        else:
            super().delete(model)

DBSession=Proxy()

def get_sessionmaker(bind=None):
    return sessionmaker(
        extension=ZopeTransactionExtension(),
        class_=MySession,
        bind=bind,
        query_cls=LimitingQuery
    )

def init_session(override_session=None, replace=False):
    global DBSession
    if DBSession.target and not replace:
        return
    if override_session:
        DBSession.target = override_session
    else:
        DBSession.target = scoped_session(get_sessionmaker())

Base=None

def init_declarative_base(override_base=None):
    global Base
    if Base:
        return
    if override_base:
        Base = override_base
    else:
        convention = {
            "ix": 'ix_%(column_0_label)s',
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
        metadata = MetaData(naming_convention=convention)
        Base = declarative_base(metadata = metadata)
        
def init_db(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
