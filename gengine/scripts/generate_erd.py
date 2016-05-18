# -*- coding: utf-8 -*-
import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars
import pyramid_dogpile_cache
from pyramid.config import Configurator

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <output_file>\n'
          '(example: "%s development.ini erd.png")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 3:
        usage(argv)
    config_uri = argv[1]
    output_file = argv[2]
    options = parse_vars(argv[3:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)
    
    durl = os.environ.get("DATABASE_URL") #heroku
    if durl:
        settings['sqlalchemy.url']=durl
        
    from eralchemy import render_er
    ## Draw from SQLAlchemy base
    render_er(settings.get("sqlalchemy.url"), output_file)
