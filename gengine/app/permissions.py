# Used in new API
perm_global_search_subjects = "global_search_subjects"
desc_global_search_subjects = "(API) Can search subjects"

# Used in new API
perm_global_manage_subjects = "global_manage_subjects"
desc_global_manage_subjects = "(API) Manage Subjects"

# Used in new API
perm_global_search_subjecttypes = "global_search_subjecttypes"
desc_global_search_subjecttypes = "(API) Can search subjecttypes"

# Used in new API
perm_global_list_variables = "global_list_variables"
desc_global_list_variables = "(API) List variables"

# Used in new API
perm_global_list_timezones = "global_list_timezones"
desc_global_list_timezones = "(API) List timezones"

# Used in new API
perm_global_manage_achievements = "global_manage_achievements"
desc_global_manage_achievements = "(API) Manage achievements"

# Old Permissions
perm_global_access_admin_ui = "global_access_admin_ui"
desc_global_access_admin_ui = "(Admin) Can access Admin-UI"

perm_own_update_subject_infos = "own_update_subject_infos"
desc_own_update_subject_infos = "Update my own infos"

perm_global_delete_subject = "global_delete_subject"
desc_global_delete_subject = "(Admin) Delete all subjects"

perm_own_delete_subject = "own_delete_subject"
desc_own_delete_subject = "Delete myself"

perm_global_increase_value = "global_increase_value"
desc_global_increase_value = "(Admin) Increase every subject's values"

perm_global_register_device = "global_register_device"
desc_global_register_device = "(Admin) Register devices for any subject"

perm_own_register_device = "own_register_device"
desc_own_register_device = "Register devices for myself"

perm_global_read_messages= "global_read_messages"
desc_global_read_messages = "(Admin) Read messages of all subjects"

perm_own_read_messages = "own_read_messages"
desc_own_read_messages = "Read own messages"


def yield_all_perms():
    for k, v in globals().items():
        if k.startswith("perm_"):
            yield (v, globals().get("desc_"+k.lstrip("perm_"), k))
