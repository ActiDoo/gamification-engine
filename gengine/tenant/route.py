
def config_routes(config):
    config.add_route('get_progress', '/t/{tenant}/progress/{user_id}', traverse="/t/{tenant}")
    config.add_route('increase_value', '/t/{tenant}/increase_value/{variable_name}/{user_id}', traverse="/t/{tenant}")
    config.add_route('increase_value_with_key', '/t/{tenant}/increase_value/{variable_name}/{user_id}/{key}', traverse="/t/{tenant}")
    config.add_route('increase_multi_values', '/t/{tenant}/increase_multi_values', traverse="/t/{tenant}")
    config.add_route('add_or_update_user', '/t/{tenant}/add_or_update_user/{user_id}', traverse="/t/{tenant}")
    config.add_route('delete_user', '/t/{tenant}/delete_user/{user_id}', traverse="/t/{tenant}")
    config.add_route('get_achievement_level', '/t/{tenant}/achievement/{achievement_id}/level/{level}', traverse="/t/{tenant}")