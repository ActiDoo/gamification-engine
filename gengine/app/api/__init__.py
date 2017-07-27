import pyramid_swagger_spec.swagger as sw
from pyramid_swagger_spec.errors import APIError

from gengine.app.permissions import perm_global_search_subjects, perm_global_manage_subjects, \
    perm_global_search_subjecttypes, perm_global_list_variables, perm_global_list_timezones, \
    perm_global_manage_achievements
from gengine.base.model import update_connection
from sqlalchemy.sql.sqltypes import Integer, String

from gengine.app.api.resources import SubjectCollectionResource, SubjectResource, SubjectTypeCollectionResource, \
    VariableCollectionResource, ApiResource
from gengine.app.api.schemas import r_status, r_subjectlist, b_subjectlist, b_subject_id, r_subjecttypelist, \
    r_variablelist, r_timezonelist, b_createachievement
from gengine.app.model import t_subjects, t_auth_users, t_auth_users_roles, t_auth_roles, t_subjecttypes_subjecttypes, \
    t_subjecttypes, t_subjects_subjects, t_variables, Achievement
from gengine.metadata import DBSession
from sqlalchemy.sql.elements import or_, not_
from sqlalchemy.sql.expression import select, and_, exists, text
import pytz
import json

from ..route import api_route

@api_route(path="/subjects", request_method="POST", name="list", context=SubjectCollectionResource, renderer='json', api=sw.api(
    tag="subjects",
    operation_id="subjects_search_list",
    summary="Lists all subjects",
    parameters=[
        sw.body_parameter(schema=b_subjectlist.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_subjectlist.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description=""""""),
        403: sw.response(schema=r_status.get_json_schema(), description="""no permission"""),
    }
))
def subjects_search_list(request, *args, **kw):
    context = request.context

    if not request.has_perm(perm_global_search_subjects):
        raise APIError(403, "forbidden")

    exclude_leaves = request.validated_params.body.get("exclude_leaves", None)
    parent_subjecttype_id = request.validated_params.body.get("parent_subjecttype_id", None)
    parent_subject_id = request.validated_params.body.get("parent_subject_id", None)

    stj = t_subjecttypes.outerjoin(t_subjecttypes_subjecttypes,
                                   t_subjecttypes_subjecttypes.c.subjecttype_id == t_subjecttypes.c.id)

    q = select([t_subjecttypes.c.id], from_obj=stj)

    if parent_subjecttype_id is not None:
        q = q.where(
            t_subjecttypes_subjecttypes.c.part_of_id == parent_subjecttype_id
        )

    if exclude_leaves is not None:
        et = t_subjecttypes_subjecttypes.alias()
        eq = select([et.c.subjecttype_id]).where(et.c.part_of_id == t_subjecttypes.c.id)
        q = q.where(exists(eq))

    subjecttype_ids = [x["id"] for x in DBSession.execute(q).fetchall()]
    cols = [
        t_subjects.c.id,
        t_subjects.c.subjecttype_id,
        t_subjects.c.name,
        t_subjects.c.lat,
        t_subjects.c.lng,
        t_subjects.c.language_id,
        t_subjects.c.timezone,
        t_subjects.c.created_at,
    ]
    j = t_subjects

    if parent_subject_id is not None:
        sq = text("""
            WITH RECURSIVE nodes_cte(subject_id, subjecttype_id, name, part_of_id, depth, path) AS (
                SELECT g1.id, g1.subjecttype_id, g1.name, NULL::bigint as part_of_id, 1::INT as depth, g1.id::TEXT as path
                FROM subjects as g1
                LEFT JOIN subjects_subjects ss ON ss.subject_id=g1.id
                WHERE ss.part_of_id = :subject_id
            UNION ALL
                SELECT c.subject_id, p.subjecttype_id, p.name, c.part_of_id, p.depth + 1 AS depth,
                    (p.path || '->' || g2.id ::TEXT)
                FROM nodes_cte AS p, subjects_subjects AS c
                JOIN subjects AS g2 ON g2.id=c.subject_id
                WHERE c.part_of_id = p.subject_id
            ) SELECT * FROM nodes_cte
        """).bindparams(subject_id=parent_subject_id)\
            .columns(subject_id=Integer, subjecttype_id=Integer,name=String,part_of_id=Integer,depth=Integer,path=String)\
            .alias()

        j = j.outerjoin(sq, sq.c.subject_id == t_subjects.c.id)
        cols += [
            sq.c.path,
            sq.c.name.label("inherited_by_name"),
            sq.c.subjecttype_id.label("inherited_by_subjecttype_id")
        ]

    subjects_query = select(cols, from_obj=j).where(t_subjects.c.subjecttype_id.in_(subjecttype_ids))

    include_search = request.validated_params.body.get("include_search", None)
    if include_search:
        subjects_query = subjects_query.where(or_(
            t_subjects.c.name.ilike("%" + include_search + "%"),
        ))

    limit = request.validated_params.body.get("limit", None)
    if limit:
        subjects_query = subjects_query.limit(limit)

    offset = request.validated_params.body.get("offset", None)
    if offset:
        subjects_query = subjects_query.offset(offset)

    result = DBSession.execute(subjects_query).fetchall()
    subjects = {}

    for r in result:
        if not r["id"] in subjects:
            path = r["path"] if "path" in r and r["path"] is not None else ""
            inherited_by_name = r["inherited_by_name"] if "inherited_by_name" in r and r["inherited_by_name"] is not None else ""
            inherited_by_subjecttype_id = r["inherited_by_subjecttype_id"] if "inherited_by_subjecttype_id" in r and r["inherited_by_subjecttype_id"] is not None else ""
            subjects[r["id"]] = {
                'id': r["id"],
                'subjecttype_id': r["subjecttype_id"],
                'name': r["name"],
                'created_at': r["created_at"],
                'path': path,
                'inherited_by_subjecttype_id': inherited_by_subjecttype_id,
                'inherited_by_name': inherited_by_name,
                'in_parent': True if path else False,
                'directly_in_parent': len(path)>0 and not "->" in path,
                'inherited_by': path.split("->")[0] if len(path)>0 and "->" in path else None
            }

    return r_subjectlist.output({
        "subjects": list(subjects.values())
    })


@api_route(path="/subjects/{parent_id}", request_method="POST", name="add_subject", context=SubjectResource, renderer='json', api=sw.api(
    tag="subjects",
    operation_id="subjects_add_to_parent",
    summary="Add a subject to a parent subject",
    parameters=[
        sw.path_parameter(name="parent_id", parameter_type=sw.Types.number),
        sw.body_parameter(schema=b_subject_id.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_status.get_json_schema()),
        403: sw.response(schema=r_status.get_json_schema()),
    }
))
def subject_add_to_parent(request, *args, **kw):
    context = request.context
    parent_row = context.subject_row

    if not request.has_perm(perm_global_manage_subjects):
        raise APIError(403, "forbidden")

    q = t_subjects_subjects.select().where(and_(
        t_subjects_subjects.c.subject_id == request.validated_params.body["subject_id"],
        t_subjects_subjects.c.part_of_id == parent_row["id"],
    ))

    r = DBSession.execute(q).fetchone()

    if not r:
        q = t_subjects_subjects.insert({
            'subject_id': request.validated_params.body["subject_id"],
            'part_of_id': parent_row["id"],
        })

        update_connection().execute(q)

    return r_status.output({
        "status": "ok"
    })


@api_route(path="/subjects/{parent_id}", request_method="POST", name="remove_subject", context=SubjectResource, renderer='json', api=sw.api(
    tag="subjects",
    operation_id="subjects_remove_from_parent",
    summary="Remove a subject from its parent",
    parameters=[
        sw.path_parameter(name="parent_id", parameter_type=sw.Types.number),
        sw.body_parameter(schema=b_subject_id.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_status.get_json_schema()),
        403: sw.response(schema=r_status.get_json_schema()),
    }
))
def subject_remove_from_parent(request, *args, **kw):
    context = request.context
    parent_row = context.subject_row

    if not request.has_perm(perm_global_manage_subjects):
        raise APIError(403, "forbidden")

    q = t_subjects_subjects.select().where(and_(
        t_subjects_subjects.c.subject_id == request.validated_params.body["subject_id"],
        t_subjects_subjects.c.part_of_id == parent_row["id"],
    ))

    r = DBSession.execute(q).fetchone()

    if r:
        q = t_subjects_subjects.delete().where(and_(
            t_subjects_subjects.c.subject_id == request.validated_params.body["subject_id"],
            t_subjects_subjects.c.part_of_id == parent_row["id"],
        ))

        update_connection().execute(q)

    return r_status.output({
        "status": "ok"
    })


@api_route(path="/subjecttypes", request_method="GET", name="list", context=SubjectTypeCollectionResource, renderer='json', api=sw.api(
    tag="subjecttypes",
    operation_id="subjecttypes_search_list",
    summary="Lists all subjecttypes",
    parameters=[
        #sw.body_parameter(schema=b_subjectlist.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_subjectlist.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description="""
        """)
    }
))
def subjecttype_search_list(request, *args, **kw):
    context = request.context

    if not request.has_perm(perm_global_search_subjecttypes):
        raise APIError(403, "forbidden")

    q = t_subjecttypes.select().order_by(t_subjecttypes.c.name.asc())
    types = DBSession.execute(q).fetchall()

    ret = {
        "subjecttypes": [{
            "id": st["id"],
            "name": st["name"],
        } for st in types]
    }

    return r_subjecttypelist.output(ret)


@api_route(path="/variables", request_method="GET", name="list", context=VariableCollectionResource, renderer='json', api=sw.api(
    tag="variables",
    operation_id="variables_search_list",
    summary="Lists all variables",
    parameters=[

    ],
    responses={
        200: sw.response(schema=r_variablelist.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description=""""""),
        403: sw.response(schema=r_status.get_json_schema(), description=""""""),
    }
))
def variables_search_list(request, *args, **kw):
    context = request.context
    q = t_variables.select().order_by(t_variables.c.name.asc())
    types = DBSession.execute(q).fetchall()

    if not request.has_perm(perm_global_list_variables):
        raise APIError(403, "forbidden")

    ret = {
        "variables": [{
            "id": st["id"],
            "name": st["name"],
            "increase_permission": st["increase_permission"],
        } for st in types]
    }

    return r_variablelist.output(ret)


@api_route(path="/", request_method="GET", name="timezones_list", context=ApiResource, renderer='json', api=sw.api(
    tag="timezones",
    operation_id="timezones_list",
    summary="Lists all timezones",
    parameters=[

    ],
    responses={
        200: sw.response(schema=r_timezonelist.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description=""""""),
        403: sw.response(schema=r_status.get_json_schema(), description=""""""),
    }
))
def timezones_list(request, *args, **kw):
    context = request.context
    timezones = pytz.common_timezones

    if not request.has_perm(perm_global_list_timezones):
        raise APIError(403, "forbidden")

    ret = {
        "timezones": [{
            "name": st,
        } for st in timezones]
    }

    return r_timezonelist.output(ret)


@api_route(path="/", request_method="POST", name="create_achievement", context=ApiResource, renderer='json', api=sw.api(
    tag="achievements",
    operation_id="create_achievement",
    summary="Create an Achievement",
    parameters=[
        sw.body_parameter(schema=b_createachievement.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_status.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description=""""""),
        403: sw.response(schema=r_status.get_json_schema(), description=""""""),
    }
))
def create_achievement(request, *args, **kw):
    context = request.context

    if not request.has_perm(perm_global_manage_achievements):
        raise APIError(403, "forbidden")

    try:
        name = request.validated_params.body.get("name", None)
        player_subjecttype_id = request.validated_params.body.get("player_subjecttype_id")
        context_subjecttype_id = request.validated_params.body.get("context_subjecttype_id")
        domain_subject_ids = request.validated_params.body.get("domain_subject_ids")
        condition = request.validated_params.body.get("condition")
        evaluation = request.validated_params.body.get("evaluation")
        evaluation_timezone = request.validated_params.body.get("evaluation_timezone")
        evaluation_shift = request.validated_params.body.get("evaluation_shift")
        valid_start = request.validated_params.body.get("valid_start")
        valid_end = request.validated_params.body.get("valid_end")
        comparison_type = request.validated_params.body.get("comparison_type")

        ach = Achievement(
            name = name,
            player_subjecttype_id = player_subjecttype_id,
            context_subjecttype_id = context_subjecttype_id,
            domain_subject_ids = domain_subject_ids,
            condition = json.dumps(condition),
            comparison_type = comparison_type,
            evaluation = evaluation,
            evaluation_timezone = evaluation_timezone,
            evaluation_shift = evaluation_shift,
            valid_start = valid_start,
            valid_end = valid_end,
        )

        DBSession.add(ach)
        DBSession.flush()

        return r_status.output({
            "status": "ok"
        })

    except:
        raise APIError(500, message="Error creating achievement")
