import pyramid_swagger_spec.swagger as sw
from pyramid_swagger_spec.schema import JSchema

r_status = JSchema(schema={
    "status": sw.property(sw.Types.string, nullable=False)
})

r_subject = JSchema(schema={
    'id': sw.property(sw.Types.string, nullable=False),
    'name': sw.property(sw.Types.string, nullable=True),
    'created_at': sw.property(sw.Types.string, nullable=False),
    'subjecttype_id': sw.property(sw.Types.string, nullable=False),
    'path': sw.property(sw.Types.string, nullable=True),
    'inherited_by_subjecttype_id': sw.property(sw.Types.number, nullable=True),
    'inherited_by_name': sw.property(sw.Types.number, nullable=False),
    'in_parent': sw.property(sw.Types.boolean, nullable=False),
    'directly_in_parent': sw.property(sw.Types.boolean, nullable=False),
    'inherited_by': sw.property(sw.Types.number, nullable=True),
})

r_subject_short = JSchema(schema={
    'id': sw.property(sw.Types.string, nullable=False),
    'name': sw.property(sw.Types.string, nullable=True),
})

r_subjectlist = JSchema(schema={
    'subjects': sw.array_property(
        items=sw.object_property(
            properties=r_subject.get_json_schema()
        )
    )
})

b_subjectlist = JSchema(schema={
    "limit": sw.property(sw.Types.number, nullable=True),
    "offset": sw.property(sw.Types.number, nullable=True),
    "include_search": sw.property(sw.Types.string, nullable=True),
    "exclude_leaves": sw.property(sw.Types.boolean, nullable=True),
    "parent_subjecttype_id": sw.property(sw.Types.number, nullable=True),
    "parent_subject_id": sw.property(sw.Types.number, nullable=True),
})

b_subject_id = JSchema(schema={
    "subject_id": sw.property(sw.Types.number, nullable=True)
})


r_subjecttype = JSchema(schema={
    'id': sw.property(sw.Types.string, nullable=False),
    'name': sw.property(sw.Types.string, nullable=False),
})

r_subjecttypelist = JSchema(schema={
    'subjecttypes': sw.array_property(
        items=sw.object_property(
            properties=r_subjecttype.get_json_schema()
        )
    )
})

r_variable = JSchema(schema={
    'id': sw.property(sw.Types.string, nullable=False),
    'name': sw.property(sw.Types.string, nullable=False),
    'increase_permission': sw.property(sw.Types.string, nullable=False),
})

r_variablelist = JSchema(schema={
    'variables': sw.array_property(
        items=sw.object_property(
            properties=r_variable.get_json_schema()
        )
    )
})


r_timezone = JSchema(schema={
    'name': sw.property(sw.Types.string, nullable=False),
})

r_timezonelist = JSchema(schema={
    'timezones': sw.array_property(
        items=sw.object_property(
            properties=r_timezone.get_json_schema()
        )
    )
})

# This currently only accepts the parameters which are needed for the leaderboard_creation form
# To be extended if needed
b_createachievement = JSchema(schema={
    'name': sw.property(sw.Types.string, nullable=False),
    'player_subjecttype_id': sw.property(sw.Types.number, nullable=False),
    'context_subjecttype_id': sw.property(sw.Types.number, nullable=True),
    'domain_subject_ids': sw.array_property(
        items=sw.property(sw.Types.number, nullable=False),
        nullable=True
    ),
    'condition': sw.property(sw.Types.object, nullable=False),
    'evaluation': sw.property(sw.Types.string, nullable=False),
    'comparison_type': sw.property(sw.Types.string, nullable=False),
    'evaluation_timezone': sw.property(sw.Types.string, nullable=False),
    'evaluation_shift': sw.property(sw.Types.number, nullable=False),
    'valid_start': sw.property(sw.Types.string, nullable=True),
    'valid_end': sw.property(sw.Types.string, nullable=True),
})

