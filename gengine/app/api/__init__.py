import pyramid_swagger_spec.swagger as sw
from gengine.app.api.resources import UserCollectionResource
from gengine.app.api.schemas import r_status, r_userlist, b_userlist
from gengine.app.model import t_users, t_auth_users, t_auth_users_roles, t_auth_roles, t_groups_groups, t_groups, \
    t_users_groups
from gengine.metadata import DBSession
from pyramid_swagger_spec.errors import APIError
from sqlalchemy.sql.elements import or_, not_
from sqlalchemy.sql.expression import select, and_, exists, text

from ..route import api_route

@api_route(path="/users", request_method="POST", name="list", context=UserCollectionResource, renderer='json', api=sw.api(
    tag="users",
    operation_id="search_list",
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
    #
    # bottom_group = t_groups_groups.alias()
    #
    # recursion = select([
    #     t_groups_groups.c.group_id.label("group_id"),
    #     t_groups_groups.c.part_of_id.label("part_of_id"),
    # ]).cte(name="recursion", recursive=True).alias()
    #
    # not_child_group = t_groups_groups.alias()
    #
    # right = recursion.union_all(recursion.union_all(
    #     select([
    #         bottom_group.c.group_id.label("group_id"),
    #         bottom_group.c.part_of_id.label("part_of_id"),
    #     ]).where(and_(
    #         bottom_group.c.part_of_id == recursion.c.group_id,
    #         not_(exists(and_(
    #             bottom_group.c.group_id == not_child_group.c.part_of_id
    #         ))),
    #         bottom_group.c.group_id == t_users_groups.c.group_id
    #     ))
    # ))

    sq = text("""
    WITH RECURSIVE nodes_cte(group_id, name, part_of_id, depth, path) AS (
        SELECT tn.group_id, g1.name, tn.part_of_id, 1::INT AS depth, g1.id::TEXT AS path
        FROM groups_groups AS tn JOIN groups g1 ON g1.id=tn.group_id
        WHERE tn.part_of_id IS NULL
    UNION ALL
        SELECT c.group_id, g2.name, c.part_of_id, p.depth + 1 AS depth,
            (p.path || '->' || g2.name ::TEXT)
        FROM nodes_cte AS p, groups_groups AS c
        JOIN groups g2 ON g2.id=c.group_id
        WHERE c.part_of_id = p.group_id
    )
    """)

    q = select([
        t_users.c.id,
        t_users.c.name,
        t_users.c.lat,
        t_users.c.lng,
        t_users.c.language_id,
        t_users.c.timezone,
        t_users.c.created_at,
        sq.c.path.label("groups")
    ], from_obj=t_users.outerjoin(
        right=t_auth_users,
        onclause=t_auth_users.c.user_id == t_users.c.id
    ).outerjoin(
        right=t_auth_users_roles,
        onclause=t_auth_users_roles.c.user_id == t_auth_users.c.user_id
    ).outerjoin(
        right=t_auth_roles,
        onclause=t_auth_roles.c.id == t_auth_users_roles.c.role_id
    ).outerjoin(
        right=t_auth_roles,
        onclause=t_auth_roles.c.id == t_auth_users_roles.c.role_id
    ).outerjoin(
        right=t_users_groups,
        onclause=t_users_groups.c.user_id == t_users.c.id
    ).outerjoin(
        right=sq,
        onclause=sq.c.group_id == t_users_groups.c.group_id
    ))

    include_search = request.validates_params.body.get("include_search", None)
    if include_search:
        q = q.where(or_(
            t_users.c.id == include_search,
            t_auth_users.c.email.ilike(include_search),
            t_auth_roles.c.name.ilike(include_search),
        ))

    include_group_id = request.validates_params.body.get("include_group_id", None)
    if include_group_id:
        q = q.where(or_(
            t_users.c.id == include_search,
            t_auth_users.c.email.ilike(include_search),
            t_auth_roles.c.name.ilike(include_search),
        ))

    result = DBSession.execute(q).fetchall()

    return r_userlist.output({
        'users': [{
            'id': u["id"],
            'name': u["name"],
            'created_at':  u["created_at"],
            'groups':  u["groups"]
        } for u in result]
    })
