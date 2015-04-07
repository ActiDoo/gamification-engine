#!/usr/bin/env python
import os
import sys

try:
    here = __file__
except NameError:
    # Python 2.2
    here = sys.argv[0]

relative_paste = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(here))), 'paste')

if os.path.exists(relative_paste):
    sys.path.insert(0, os.path.dirname(relative_paste))

from paste.script import command
command.run()
