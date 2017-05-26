import sys
import os
import json

from gengine.base.settings import get_settings


def includeme(config):
    config.add_static_view(name='admin/jsstatic', path='gengine:app/jsscripts/build/static')

def get_jsmain():
    debug = get_settings().get("load_from_webpack_dev_server", False)
    if debug:
        return "http://localhost:3000/static/js/bundle.js"
    else:
        modpath = os.path.dirname(sys.modules[__name__].__file__)

        buildpath = os.path.join(modpath, "build")
        with open(os.path.join(buildpath, "asset-manifest.json"), "r") as f:
            manifest = json.load(f)

            return "/admin/jsstatic/"+manifest["main.js"].lstrip("static/")

        return None

def get_cssmain():
    debug = get_settings().get("load_from_webpack_dev_server", False)
    if debug:
        return "http://localhost:3000/static/js/bundle.js"
    else:
        modpath = os.path.dirname(sys.modules[__name__].__file__)

        buildpath = os.path.join(modpath, "build")
        with open(os.path.join(buildpath, "asset-manifest.json"), "r") as f:
            manifest = json.load(f)

            return "/admin/jsstatic/"+manifest["main.css"].lstrip("static/")

        return None
