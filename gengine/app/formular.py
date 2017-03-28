import re

import functools
import jsl
import json
import jsonschema
import pyparsing as pp

import math
import operator

from sqlalchemy.sql import and_, or_

class FormularEvaluationException(Exception):
    def __init__(self, message):
        self.message = message

# The Expression Parser for mathematical formulars
class NumericStringParser(object):
    '''
    Most of this code comes from the fourFn.py pyparsing example

    # from: http://stackoverflow.com/a/2371789

    '''

    def pushFirst(self, strg, loc, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, strg, loc, toks):
        if toks and toks[0] == '-':
            self.exprStack.append('unary -')

    def __init__(self, extra_literals=[]):
        """
        expop   :: '^'
        multop  :: '*' | '/'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        point = pp.Literal(".")
        e = pp.CaselessLiteral("E")
        fnumber = pp.Combine(pp.Word("+-" + pp.nums, pp.nums) +
                             pp.Optional(point + pp.Optional(pp.Word(pp.nums))) +
                             pp.Optional(e + pp.Word("+-" + pp.nums, pp.nums)))
        ident = pp.Word(pp.alphas, pp.alphas + pp.nums + "_$")
        plus = pp.Literal("+")
        minus = pp.Literal("-")
        mult = pp.Literal("*")
        div = pp.Literal("/")
        lpar = pp.Literal("(").suppress()
        rpar = pp.Literal(")").suppress()
        addop = plus | minus
        multop = mult | div
        expop = pp.Literal("^")
        pi = pp.CaselessLiteral("PI")

        self.extra_literals = extra_literals
        pp_extra_literals = functools.reduce(operator.or_, [pp.CaselessLiteral(e) for e in extra_literals], pp.NoMatch())

        expr = pp.Forward()
        atom = ((pp.Optional(pp.oneOf("- +")) +
                 (pi | e | pp_extra_literals | fnumber | ident + lpar + expr + rpar).setParseAction(self.pushFirst))
                | pp.Optional(pp.oneOf("- +")) + pp.Group(lpar + expr + rpar)
                ).setParseAction(self.pushUMinus)
        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = pp.Forward()
        factor << atom + pp.ZeroOrMore((expop + factor).setParseAction(self.pushFirst))
        term = factor + pp.ZeroOrMore((multop + factor).setParseAction(self.pushFirst))
        expr << term + pp.ZeroOrMore((addop + term).setParseAction(self.pushFirst))
        # addop_term = ( addop + term ).setParseAction( self.pushFirst )
        # general_term = term + ZeroOrMore( addop_term ) | OneOrMore( addop_term)
        # expr <<  general_term
        self.bnf = expr
        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {"+": operator.add,
                    "-": operator.sub,
                    "*": operator.mul,
                    "/": operator.truediv,
                    "^": operator.pow}
        self.fn = {"sin": math.sin,
                   "cos": math.cos,
                   "tan": math.tan,
                   "abs": abs,
                   "trunc": lambda a: int(a),
                   "round": round,
                   "sgn": lambda a: abs(a) > epsilon and pp.cmp(a, 0) or 0}

    def evaluateStack(self, s, key_value_map={}):
        op = s.pop()
        if op == 'unary -':
            return -self.evaluateStack(s, key_value_map)
        if op in "+-*/^":
            op2 = self.evaluateStack(s, key_value_map)
            op1 = self.evaluateStack(s, key_value_map)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op in self.extra_literals:
            return key_value_map[op]
        elif op in self.fn:
            return self.fn[op](self.evaluateStack(s, key_value_map))
        elif op[0].isalpha():
            return 0
        else:
            return float(op)

    def eval(self, num_string, key_value_map={}, parseAll=True):
        self.exprStack = []
        results = self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:], key_value_map = key_value_map)
        return val


def evaluate_value_expression(expression, params={}):
    if expression is None:
        return None
    try:
        nsp = NumericStringParser(extra_literals=params.keys())
        return nsp.eval(expression,key_value_map=params)
    except:
        raise FormularEvaluationException(expression)


def render_string(tpl, params):
    """Substitute text in <> with corresponding variable value."""
    regex = re.compile('\${(.+?)}')
    def repl(m):
        group = m.group(1)
        value = evaluate_value_expression(group, params)
        if int(value) == value:
            value = int(value)
        return str(value)
    return regex.sub(repl, tpl)


def evaluate_string(inst, params=None):
    try:
        if inst is None:
            return None
        if params is not None:
            formatted = render_string(inst, params)
        else:
            formatted = inst

        try:
            if str(int(formatted)) == str(formatted):
                return int(formatted)
        except:
            pass

        try:
            if str(int(float)) == str(float):
                return float(formatted)
        except:
            pass

        return formatted
    except:
        raise FormularEvaluationException(inst)


# The condition JSON-Schema
class Conjunction(jsl.Document):
    terms = jsl.ArrayField(jsl.OneOfField([
        jsl.DocumentField("Conjunction", as_ref=True),
        jsl.DocumentField("Disjunction", as_ref=True),
        jsl.DocumentField("Literal", as_ref=True)
    ], required=True), required=True)
    type = jsl.StringField(pattern="^conjunction$")


class Disjunction(jsl.Document):
    terms = jsl.ArrayField(jsl.OneOfField([
        jsl.DocumentField("Conjunction", as_ref=True),
        jsl.DocumentField("Disjunction", as_ref=True),
        jsl.DocumentField("Literal", as_ref=True)
    ], required=True), required=True)
    type = jsl.StringField(pattern="^disjunction$")


class Literal(jsl.Document):
    variable = jsl.StringField(required=True)
    key_operator = jsl.StringField(pattern = "^(IN|ILIKE)$", required=False)
    key = jsl.ArrayField(jsl.StringField(), required=False)
    type = jsl.StringField(pattern="^literal$")


class TermDocument(jsl.Document):
    term = jsl.OneOfField([
        jsl.DocumentField(Conjunction, as_ref=True),
        jsl.DocumentField(Disjunction, as_ref=True),
        jsl.DocumentField(Literal, as_ref=True)
    ], required=True)


def validate_term(condition_term):
    return jsonschema.validate(condition_term, TermDocument.get_schema())

def _term_eval(term, column_variable, column_key):

    if term["type"].lower() == "conjunction":
        return and_(*((_term_eval(t, column_variable, column_key) for t in term["terms"])))
    elif term["type"].lower() == "disjunction":
        return or_(*((_term_eval(t, column_variable, column_key) for t in term["terms"])))
    elif term["type"].lower() == "literal":
        if "key" in term and term["key"]:
            key_operator = term.get("key_operator", "IN")
            if key_operator is None or key_operator == "IN":
                key_condition = column_key.in_(term["key"])
            elif key_operator=="ILIKE":
                key_condition = or_(*(column_key.ilike(pattern) for pattern in term["key"]))
            return and_(column_variable==term["variable"], key_condition)
        else:
            return column_variable==term["variable"]


def evaluate_condition(inst, column_variable=None, column_key=None):
    try:
        if isinstance(inst,str):
            inst = json.loads(inst)
        from gengine.app.model import t_values, t_variables
        if column_variable is None:
            column_variable = t_variables.c.name.label("variable_name")
        if column_key is None:
            column_key = t_variables.c.name.label("variable_name")

        jsonschema.validate(inst, TermDocument.get_schema())
        return _term_eval(inst["term"], column_variable, column_key)
    except:
       raise FormularEvaluationException(json.dumps(inst))


demo_schema = {
    'term': {
        'variable': 'participate',
        'key_operator': 'IN',
        'key': ['2', ],
        'type': 'literal'
    }
}

demo2_schema = {
    'term': {
        'type': 'disjunction',
        'terms': [
            {
                'type': 'literal',
                'variable': 'participate',
                'key_operator': 'ILIKE',
                'key': ['%blah%', ]
            },
            {
                'type': 'literal',
                'variable': 'participate',
                'key_operator': 'IN',
                'key': ['2', ]
            }
        ]
    }
}
