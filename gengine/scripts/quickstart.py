# -*- coding: utf-8 -*-
import os
import sys
import gengine
import shutil

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <directory>\n' % (cmd,))
    sys.exit(1)
 
def copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    except shutil.Error as e:
        print('Error: %s' % e)
    except OSError as e:
        print('Error: %s' % e)

def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    
    directory = argv[1]
    
    if not os.path.exists(directory):
        
        #copy files
        quickstart_template_path = os.path.join(os.path.dirname(gengine.__path__[0]), "gengine_quickstart_template")
                
        copyDirectory(quickstart_template_path, directory)
        
    else:
        print "directory already exists"
