import logging
log = logging.getLogger(__name__)

"""

From: http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/resources.html
The __parent__ attribute of a location-aware resource should be a reference to the resource's parent resource instance in the tree. The __name__ attribute should be the name with which a resource's parent refers to the resource via __getitem__.

The __parent__ of the root resource should be None and its __name__ should be the empty string. For instance:

"""


# RootResourceFactory
from pyramid.security import Allow, DENY_ALL

from ..model import t_users


def root_factory(request):
    return RootResource(request=request)


# RootResource
class RootResource(dict):
    def __init__(self, *args, **kw):
        request = kw.pop("request")
        super(RootResource, self).__init__(*args, **kw)
        self['api'] = ApiResource(t_name='api', t_parent=self, request=request)


# LocationAware BaseResource
class BaseResource(object):
    def __init__(self, t_name="", t_parent=None, request=None, *args, **kw):
        super(BaseResource, self).__init__(*args, **kw)
        self.d = dict()
        self.__name__ = t_name
        self.__parent__ = t_parent
        self.request = request

    def __getitem__(self, item):
        return self.d[item]

    def __setitem__(self, key, value):
        self.d[key] = value


class ApiResource(BaseResource):
    def __init__(self, *args, **kw):
        super(ApiResource, self).__init__(*args, **kw)
        self['users'] = UserCollectionResource(request=self.request, t_name='users', t_parent=self)


class UserCollectionResource(BaseResource):
    def __init__(self, *args, **kw):
        super(UserCollectionResource, self).__init__(*args, **kw)

    def __getitem__(self, user_id):
        try:
            row = self.request.dbsession.execute(t_users.select().where(t_users.c.id == user_id)).fetchone()
            if row:
                return UserResource(request=self.request, t_name=user_id, t_parent=self, user_id=user_id, user_row=row)
            else:
                raise KeyError()
        except Exception as e:
            log.exception("Error creating UserResource")
            raise KeyError()


class UserResource(BaseResource):
    def __init__(self, user_id, user_row, *args, **kw):
        super(UserResource, self).__init__(*args, **kw)
        self.user_id = user_id
        self.user_row = user_row
        self.__acl__ = [
            (Allow, 'user:%(user_id)s' % {'user_id': user_row["id"]}, tuple()),
            DENY_ALL
        ]
