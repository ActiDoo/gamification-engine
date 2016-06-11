import sys
from sqlalchemy.sql.expression import and_, or_

if sys.version_info < (3,5):
    import __builtin__
else:
    import builtins as __builtin__

safe_list = ['math', 'acos', 'asin', 'atan', 'atan2', 'ceil',
             'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor',
             'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 'modf',
             'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'sum', 'range', 'str', 'int', 'float']

# use the list to filter the local namespace
from math import *

safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
for k in safe_dict.keys():
    if safe_dict[k] is None:
        if hasattr(__builtin__, k):
            safe_dict[k] = getattr(__builtin__, k)
safe_dict['and_'] = and_
safe_dict['or_'] = or_
safe_dict['abs'] = abs

class FormularEvaluationException(Exception):
    pass

class DictObjectProxy():
    obj = None

    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, name):
        if not name in self.obj:
            return ""
        return self.obj[name]

# TODO: Cache
def eval_formular(s, params={}):
    """evaluates the formular.

    parameters are available as p.name,

    available math functions:
    'math','acos', 'asin', 'atan', 'atan2', 'ceil',
    'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor',
    'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 'modf',
    'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'sum', 'range'
    """
    try:
        if s is None:
            return None
        else:
            p = DictObjectProxy(params)

            # add any needed builtins back in.
            safe_dict['p'] = p

            result = eval(s, {"__builtins__": None}, safe_dict)
            if type(result) == str:
                return result % params
            else:
                return result
    except:
        raise FormularEvaluationException(s)