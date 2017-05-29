import pyramid_swagger_spec.swagger as sw
from gengine.base.model import update_connection
from sqlalchemy.sql.sqltypes import Integer, String

from gengine.app.api.resources import UserCollectionResource, GroupCollectionResource, GroupResource
from gengine.app.api.schemas import r_status, r_userlist, b_userlist, r_grouplist, b_grouplist, r_group_details, \
    b_user_id
from gengine.app.model import t_users, t_auth_users, t_auth_users_roles, t_auth_roles, t_groups_groups, t_groups, \
    t_users_groups
from gengine.metadata import DBSession
from pyramid_swagger_spec.errors import APIError
from sqlalchemy.sql.elements import or_, not_
from sqlalchemy.sql.expression import select, and_, exists, text

from ..route import api_route

@api_route(path="/users", request_method="POST", name="list", context=UserCollectionResource, renderer='json', api=sw.api(
    tag="users",
    operation_id="users_search_list",
    summary="Lists all users",
    parameters=[
        sw.body_parameter(schema=b_userlist.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_userlist.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description="""
        """)
    }
))
def users_search_list(request, *args, **kw):
    context = request.context

    include_group_id = request.validated_params.body.get("include_group_id", None)
    exclude_group_id = request.validated_params.body.get("exclude_group_id", None)

    sq = text("""
    WITH RECURSIVE nodes_cte(group_id, name, part_of_id, depth, path) AS (
        SELECT g1.id, g1.name, NULL::bigint as part_of_id, 1::INT as depth, g1.id::TEXT as path
        FROM groups as g1
        WHERE NOT EXISTS(SELECT * FROM groups_groups WHERE group_id=g1.id)
    UNION ALL
        SELECT c.group_id, g2.name, c.part_of_id, p.depth + 1 AS depth,
            (p.path || '->' || g2.id ::TEXT)
        FROM nodes_cte AS p, groups_groups AS c
        JOIN groups AS g2 ON g2.id=c.group_id
        WHERE c.part_of_id = p.group_id
    ) SELECT * FROM nodes_cte
        """).columns(group_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()

    j =t_users.outerjoin(
        right=t_auth_users,
        onclause=t_auth_users.c.user_id == t_users.c.id
    ).outerjoin(
        right=t_auth_users_roles,
        onclause=t_auth_users_roles.c.user_id == t_auth_users.c.user_id
    ).outerjoin(
        right=t_auth_roles,
        onclause=t_auth_roles.c.id == t_auth_users_roles.c.role_id
    ).outerjoin(
        right=t_users_groups,
        onclause=t_users_groups.c.user_id == t_users.c.id
    ).outerjoin(
        right=sq,
        onclause=sq.c.group_id == t_users_groups.c.group_id
    )

    cols = [
        t_users.c.id,
        t_users.c.name,
        t_users.c.lat,
        t_users.c.lng,
        t_users.c.language_id,
        t_users.c.timezone,
        t_users.c.created_at,
        sq.c.path.label("group_path"),
        sq.c.group_id.label("group_id"),
        sq.c.name.label("group_name")
    ]

    if include_group_id is not None:
        sq_include_group = text("""
        WITH RECURSIVE nodes_cte(group_id, name, part_of_id, depth, path) AS (
            SELECT gi1.id, gi1.name, NULL::bigint as part_of_id, 1::INT as depth, gi1.id::TEXT as path
            FROM groups as gi1
            WHERE gi1.id=:part_of_id
        UNION ALL
            SELECT c.group_id, gi2.name, c.part_of_id, p.depth + 1 AS depth,
                (p.path || '->' || gi2.id ::TEXT)
            FROM nodes_cte AS p, groups_groups AS c
            JOIN groups AS gi2 ON gi2.id=c.group_id
            WHERE c.part_of_id = p.group_id
        ) SELECT * FROM nodes_cte
        """).bindparams(part_of_id=include_group_id).columns(group_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()

        j = j.join(sq_include_group, sq_include_group.c.group_id  == t_users_groups.c.group_id)

    q = select(cols, from_obj=j)

    include_search = request.validated_params.body.get("include_search", None)
    if include_search:
        q = q.where(or_(
            t_users.c.name.ilike("%"+include_search+"%"),
            t_auth_users.c.email.ilike("%"+include_search+"%"),
            #t_auth_roles.c.name.ilike(include_search),
        ))

    if exclude_group_id:
        sq_exclude_group = text("""
            WITH RECURSIVE nodes_cte(group_id, name, part_of_id, depth, path) AS (
                SELECT ge1.id, ge1.name, NULL::bigint as part_of_id, 1::INT as depth, ge1.id::TEXT as path
                FROM groups as ge1
                WHERE ge1.id=:ex_part_of_id
            UNION ALL
                SELECT c.group_id, ge2.name, c.part_of_id, p.depth + 1 AS depth,
                    (p.path || '->' || ge2.id ::TEXT)
                FROM nodes_cte AS p, groups_groups AS c
                JOIN groups AS ge2 ON ge2.id=c.group_id
                WHERE c.part_of_id = p.group_id
            ) SELECT * FROM nodes_cte
            """).bindparams(ex_part_of_id=exclude_group_id).columns(group_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()
        ug = t_users_groups.alias()
        ej = sq_exclude_group.join(ug, ug.c.group_id==sq_exclude_group.c.group_id)
        q = q.where(not_(exists(select([sq_exclude_group.c.group_id], from_obj=ej)\
                                .where(ug.c.user_id == t_users.c.id))))

    result = DBSession.execute(q).fetchall()
    users = {}

    for r in result:
        if not r["id"] in users:
            users[r["id"]] = {
                'id': r["id"],
                'name': r["name"],
                'created_at': r["created_at"],
                'groups': []
            }
        users[r["id"]]["groups"].append({
            "id": r["group_id"],
            "name": r["group_name"],
            "path": r["group_path"],
        })

    return r_userlist.output({
        "users": list(users.values())
    })


@api_route(path="/groups", request_method="POST", name="list", context=GroupCollectionResource, renderer='json', api=sw.api(
    tag="groups",
    operation_id="groups_search_list",
    summary="Lists all groups",
    parameters=[
        sw.body_parameter(schema=b_grouplist.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_grouplist.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description="""
        """)
    }
))
def group_search_list(request, *args, **kw):
    context = request.context

    part_of_id = request.validated_params.body.get("part_of_id", None)

    if part_of_id is not None:
        sq = text("""
        WITH RECURSIVE nodes_cte(group_id, name, part_of_id, depth, path) AS (
            SELECT g1.id, g1.name, NULL::bigint as part_of_id, 1::INT as depth, g1.id::TEXT as path
            FROM groups as g1
            WHERE EXISTS(SELECT * FROM groups_groups WHERE group_id=g1.id AND part_of_id=:part_of_id)
        UNION ALL
            SELECT c.group_id, g2.name, c.part_of_id, p.depth + 1 AS depth,
                (p.path || '->' || g2.id ::TEXT)
            FROM nodes_cte AS p, groups_groups AS c
            JOIN groups AS g2 ON g2.id=c.group_id
            WHERE c.part_of_id = p.group_id
        ) SELECT * FROM nodes_cte
        """).bindparams(part_of_id=part_of_id).columns(group_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()
    else:
        sq = text("""
        WITH RECURSIVE nodes_cte(group_id, name, part_of_id, depth, path) AS (
            SELECT g1.id, g1.name, NULL::bigint as part_of_id, 1::INT as depth, g1.id::TEXT as path
            FROM groups as g1
            WHERE NOT EXISTS(SELECT * FROM groups_groups WHERE group_id=g1.id)
        UNION ALL
            SELECT c.group_id, g2.name, c.part_of_id, p.depth + 1 AS depth,
                (p.path || '->' || g2.id ::TEXT)
            FROM nodes_cte AS p, groups_groups AS c
            JOIN groups AS g2 ON g2.id=c.group_id
            WHERE c.part_of_id = p.group_id
        ) SELECT * FROM nodes_cte
        """).columns(group_id=Integer, name=String, part_of_id=Integer, depth=Integer, path=String).alias()

    q = select([
        sq.c.group_id.label("group_id"),
        sq.c.name.label("group_name"),
        sq.c.path.label("group_path"),
        t_users.c.id.label("user_id"),
        t_users.c.name.label("user_name"),
    ], from_obj=sq.join(
        t_groups, t_groups.c.id == sq.c.group_id
    ).outerjoin(
        right=t_users_groups,
        onclause=sq.c.group_id == t_users_groups.c.group_id
    ).outerjoin(
        right=t_users,
        onclause=t_users_groups.c.user_id == t_users.c.id
    ))

    include_search = request.validated_params.body.get("include_search", None)
    if include_search:
        q = q.where(or_(
            sq.c.name.ilike("%"+include_search+"%"),
        ))

    groups = dict()

    for r in DBSession.execute(q).fetchall():
        if not r["group_id"] in groups:
            groups[r["group_id"]] = {
                "id": r["group_id"],
                "name": r["group_name"],
                "users": [],
            }

        groups[r["group_id"]]["users"].append({
            "id": r["user_id"],
            "name": r["user_name"],
        })


    return r_grouplist.output({
        'groups': list(groups.values())
    })

@api_route(path="/groups/{group_id}", request_method="GET", name="details", context=GroupResource, renderer='json', api=sw.api(
    tag="groups",
    operation_id="group_details",
    summary="Get a single groups",
    parameters=[
        sw.path_parameter(name="group_id", parameter_type=sw.Types.number),
    ],
    responses={
        200: sw.response(schema=r_group_details.get_json_schema()),
        400: sw.response(schema=r_status.get_json_schema(), description="""
        """)
    }
))
def group_details(request, *args, **kw):
    context = request.context

    return r_group_details.output({
        "id": context.group_row["group_id"],
        "name": context.group_row["group_name"],
    })


@api_route(path="/groups/{group_id}", request_method="POST", name="add_user", context=GroupResource, renderer='json', api=sw.api(
    tag="groups",
    operation_id="groups_add_user",
    summary="Add a user to a group",
    parameters=[
        sw.path_parameter(name="group_id", parameter_type=sw.Types.number),
        sw.body_parameter(schema=b_user_id.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_status.get_json_schema())
    }
))
def group_add_user(request, *args, **kw):
    context = request.context
    group_row = context.group_row

    q = t_users_groups.select().where(and_(
        t_users_groups.c.user_id == request.validated_params.body["user_id"],
        t_users_groups.c.group_id == group_row["id"],
    ))

    r = DBSession.execute(q).fetchone()

    if not r:
        q = t_users_groups.insert({
            'user_id': request.validated_params.body["user_id"],
            'group_id': group_row["id"],
        })

        update_connection().execute(q)

    return r_status.output({
        "status": "ok"
    })


@api_route(path="/groups/{group_id}", request_method="POST", name="remove_user", context=GroupResource, renderer='json', api=sw.api(
    tag="groups",
    operation_id="groups_remove_user",
    summary="Remove a user from a group",
    parameters=[
        sw.path_parameter(name="group_id", parameter_type=sw.Types.number),
        sw.body_parameter(schema=b_user_id.get_json_schema()),
    ],
    responses={
        200: sw.response(schema=r_status.get_json_schema())
    }
))
def group_remove_user(request, *args, **kw):
    context = request.context
    group_row = context.group_row

    q = t_users_groups.select().where(and_(
        t_users_groups.c.user_id == request.validated_params.body["user_id"],
        t_users_groups.c.group_id == group_row["id"],
    ))

    r = DBSession.execute(q).fetchone()

    if r:
        q = t_users_groups.delete().where(and_(
            t_users_groups.c.user_id == request.validated_params.body["user_id"],
            t_users_groups.c.group_id == group_row["id"],
        ))

        update_connection().execute(q)

    return r_status.output({
        "status": "ok"
    })
