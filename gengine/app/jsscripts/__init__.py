import sys
import os
import json

from gengine.base.settings import get_settings
from gengine.base.util import lstrip_word
from pyramid.settings import asbool

def includeme(config):
    config.add_static_view(name='admin/jsstatic', path='gengine:app/jsscripts/build/static')

def get_jsmain():
    debug = asbool(get_settings().get("load_from_webpack_dev_server", False))
    if debug:
        return "http://localhost:3000/static/js/bundle.js"
    else:
        modpath = os.path.dirname(sys.modules[__name__].__file__)

        buildpath = os.path.join(modpath, "build")
        with open(os.path.join(buildpath, "asset-manifest.json"), "r") as f:
            manifest = json.load(f)
            return "/admin/jsstatic/"+lstrip_word(manifest["main.js"], "static/")

        return None

def get_cssmain():
    debug = asbool(get_settings().get("load_from_webpack_dev_server", False))
    if debug:
        return "http://localhost:3000/static/css/bundle.css"
    else:
        modpath = os.path.dirname(sys.modules[__name__].__file__)

        buildpath = os.path.join(modpath, "build")
        with open(os.path.join(buildpath, "asset-manifest.json"), "r") as f:
            manifest = json.load(f)
            return "/admin/jsstatic/"+lstrip_word(manifest["main.css"],"static/")

        return None
