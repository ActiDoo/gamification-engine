import logging

from gengine.app.model import t_variables, t_achievements
from gengine.app.model import t_subjecttypes

log = logging.getLogger(__name__)

"""

From: http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/resources.html
The __parent__ attribute of a location-aware resource should be a reference to the resource's parent resource instance in the tree. The __name__ attribute should be the name with which a resource's parent refers to the resource via __getitem__.

The __parent__ of the root resource should be None and its __name__ should be the empty string. For instance:

"""


# RootResourceFactory
from pyramid.security import Allow, DENY_ALL

from ..model import t_subjects


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
        self['subjects'] = SubjectCollectionResource(request=self.request, t_name='subjects', t_parent=self)
        self['subjecttypes'] = SubjectTypeCollectionResource(request=self.request, t_name='subjecttypes', t_parent=self)
        self['variables'] = VariableCollectionResource(request=self.request, t_name='variables', t_parent=self)
        self['achievements'] = AchievementCollectionResource(request=self.request, t_name='achievements', t_parent=self)


class AchievementCollectionResource(BaseResource):
    def __init__(self, *args, **kw):
        super(AchievementCollectionResource, self).__init__(*args, **kw)

    def __getitem__(self, achievement_id):
        try:
            from gengine.metadata import DBSession
            row = DBSession.execute(t_achievements.select().where(t_achievements.c.id == int(achievement_id))).fetchone()
            if row:
                return AchievementResource(request=self.request, t_name=achievement_id, t_parent=self, achievement_id=achievement_id, achievement_row=row)
        except ValueError:
            pass
        except:
            log.exception("Error creating AchievementResource")
        raise KeyError()


class AchievementResource(BaseResource):
    def __init__(self, achievement_id, achievement_row, *args, **kw):
        super(AchievementResource, self).__init__(*args, **kw)
        self.achievement_id = achievement_id
        self.achievement_row = achievement_row


class SubjectCollectionResource(BaseResource):
    def __init__(self, *args, **kw):
        super(SubjectCollectionResource, self).__init__(*args, **kw)

    def __getitem__(self, subject_id):
        try:
            from gengine.metadata import DBSession
            row = DBSession.execute(t_subjects.select().where(t_subjects.c.id == int(subject_id))).fetchone()
            if row:
                return SubjectResource(request=self.request, t_name=subject_id, t_parent=self, subject_id=subject_id, subject_row=row)
        except ValueError:
            pass
        except:
            log.exception("Error creating SubjectResource")
        raise KeyError()


class SubjectResource(BaseResource):
    def __init__(self, subject_id, subject_row, *args, **kw):
        super(SubjectResource, self).__init__(*args, **kw)
        self.subject_id = subject_id
        self.subject_row = subject_row

class SubjectTypeCollectionResource(BaseResource):
    def __init__(self, *args, **kw):
        super(SubjectTypeCollectionResource, self).__init__(*args, **kw)

    def __getitem__(self, subjecttype_id):
        try:
            from gengine.metadata import DBSession
            row = DBSession.execute(t_subjecttypes.select().where(t_subjecttypes.c.id == int(subjecttype_id))).fetchone()
            if row:
                return SubjectTypeResource(request=self.request, t_name=subjecttype_id, t_parent=self, subjecttype_id=subjecttype_id, subjecttype_row=row)
        except ValueError:
            pass
        except:
            log.exception("Error creating SubjectTypeResource")
        raise KeyError()


class SubjectTypeResource(BaseResource):
    def __init__(self, subjecttype_id, subjecttype_row, *args, **kw):
        super(SubjectTypeResource, self).__init__(*args, **kw)
        self.subjecttype_id = subjecttype_id
        self.subjecttype_row = subjecttype_row


class VariableCollectionResource(BaseResource):
    def __init__(self, *args, **kw):
        super(VariableCollectionResource, self).__init__(*args, **kw)

    def __getitem__(self, variable_id):
        try:
            from gengine.metadata import DBSession
            row = DBSession.execute(t_variables.select().where(t_variables.c.id == int(variable_id))).fetchone()
            if row:
                return VariableResource(request=self.request, t_name=variable_id, t_parent=self, variable_id=variable_id, variable_row=row)
        except ValueError:
            pass
        except:
            log.exception("Error creating SubjectTypeResource")
        raise KeyError()


class VariableResource(BaseResource):
    def __init__(self, variable_id, variable_row, *args, **kw):
        super(VariableResource, self).__init__(*args, **kw)
        self.variable_id = variable_id
        self.variable_row = variable_row
