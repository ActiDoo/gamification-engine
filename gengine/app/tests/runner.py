from gengine.app.tests import db as db
from gengine.metadata import init_declarative_base, init_session
import unittest
import os
import pkgutil

init_session()
init_declarative_base()

__path__ = [x[0] for x in os.walk(os.path.dirname(__file__))]

def create_test_suite():
    suite = unittest.TestSuite()
    for imp, modname, _ in pkgutil.walk_packages(__path__):
        mod = imp.find_module(modname).load_module(modname)
        for test in unittest.defaultTestLoader.loadTestsFromModule(mod):
            suite.addTests(test)
    return suite

if __name__=="__main__":
    try:
        db.setupDB()
        testSuite = create_test_suite()
        text_runner = unittest.TextTestRunner().run(testSuite)
    finally:
        db.unsetupDB()
