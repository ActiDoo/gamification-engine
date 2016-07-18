
perm_global_access_admin_ui = "global_access_admin_ui"
desc_global_access_admin_ui = "(Admin) Can access Admin-UI"

perm_global_update_user_infos = "global_update_user_infos"
desc_global_update_user_infos = "(Admin) Update every user's information"

perm_own_update_user_infos = "own_update_user_infos"
desc_own_update_user_infos = "Update my own infos"

perm_global_delete_user = "global_delete_user"
desc_global_delete_user = "(Admin) Delete all users"

perm_own_delete_user = "own_delete_user"
desc_own_delete_user = "Delete myself"

perm_global_increase_value = "global_increase_value"
desc_global_increase_value = "(Admin) Increase every user's values"

perm_global_register_device = "global_register_device"
desc_global_register_device = "(Admin) Register devices for any user"

perm_own_register_device = "own_register_device"
desc_own_register_device = "Register devices for myself"

perm_global_read_messages= "global_read_messages"
desc_global_read_messages = "(Admin) Read messages of all users"

perm_own_read_messages = "perm_own_read_messages"
desc_own_read_messages = "Read own messages"

def yield_all_perms():
    for k,v in globals().items():
        if k.startswith("perm_"):
            yield (v, globals().get("desc_"+k.lstrip("perm_"),k))
