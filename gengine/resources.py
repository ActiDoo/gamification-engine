from sqlalchemy.sql.expression import select

from gengine.metadata import DBSession
from gengine.olymp.model import t_tenants
from gengine.base.context import get_context

def root_factory(request):
    return RootResource()

class RootResource():
    def __getitem__(self, item):
        get_context().tenant = None
        DBSession.execute("SET search_path TO olymp")
        if item=="t":
            return TenantCollectionResource(self, "t")
        raise KeyError()

class TenantCollectionResource():
    def __init__(self, parent, name):
        self.__name__ = name
        self.__parent__ = parent

    def __getitem__(self, item):
        q = select([t_tenants.c.id,], from_obj = t_tenants).where(t_tenants.c.id==item)
        tenant = DBSession.execute(q).fetchone()
        if tenant:
            get_context().tenant = tenant
            DBSession.execute("SET search_path TO t_%s" % (tenant["id"],))
            return TenantResource(self, tenant)
        raise KeyError()

class TenantResource():
    def __init__(self, parent, tenant):
        self.__name__ = tenant["id"]
        self.__parent__ = parent
        self.model = tenant
