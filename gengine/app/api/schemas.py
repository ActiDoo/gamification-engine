import pyramid_swagger_spec.swagger as sw
from pyramid_swagger_spec.schema import JSchema

r_status = JSchema(schema={
    "status": sw.property(sw.Types.string, nullable=False)
})

r_user = JSchema(schema={
    'id': sw.property(sw.Types.string, nullable=False),
    'name': sw.property(sw.Types.string, nullable=True),
    'created_at': sw.property(sw.Types.string, nullable=False),
    'groups': sw.property(sw.Types.string, nullable=False),
})

r_userlist = JSchema(schema={
    'users': sw.array_property(
        items=sw.object_property(
            properties=r_user.get_json_schema()
        )
    )
})

b_userlist = JSchema(schema={
    "limit": sw.property(sw.Types.number, nullable=False),
    "offset": sw.property(sw.Types.number, nullable=False),
    "order": sw.property(sw.Types.string, nullable=False),
    "include_search": sw.property(sw.Types.string, nullable=False),
    "include_group_id": sw.property(sw.Types.number, nullable=False),
    "exclude_group_id": sw.property(sw.Types.number, nullable=False),
    "include_role_id": sw.property(sw.Types.number, nullable=False),
    "exclude_role_id": sw.property(sw.Types.number, nullable=False),
})