# -*- coding: utf-8 -*-
from pymemcache.client import Client

host = "localhost"
port = 11211
urlprefix = ""
is_active = True
urlcacheid = "gengine"

def setup_urlcache(prefix, url, active, id):
    global urlprefix, host, port, is_active, urlcacheid
    urlprefix = prefix
    host, port = url.split(":")
    port = int(port)
    is_active = active
    urlcacheid = id

def __build_key(key):
    return "::URL_CACHE::"+str(urlcacheid)+"::"+urlprefix+str(key)

def get_or_set(key,generator):
    if is_active:
        client = Client((host,port))
        key = __build_key(key)
        result = client.get(key)
        if not result:
            result = generator()
            client.set(key, result)
        client.quit()
        return result
    else:
        return generator()
    
def set_value(key,value):
    if is_active:
        client = Client((host,port))
        key = __build_key(key)
        client.set(key, value)
        client.quit()

def invalidate(key):
    if is_active:
        key = __build_key(key)
        client = Client((host,port))
        client.delete(key)
        client.quit()
    
def invalidate_all():
    if is_active:
        client = Client((host,port))
        client.flush_all()
        client.quit()