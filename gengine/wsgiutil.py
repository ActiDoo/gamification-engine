# -*- coding: utf-8 -*-

force_https = False

def init_reverse_proxy(settings_force_https,settings_prefix):
    global force_https,prefix
    force_https = settings_force_https
    prefix = settings_prefix

class HTTPSProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if force_https:
            environ['wsgi.url_scheme'] = "https"
        return self.app(environ, start_response)
    