import jsl
import jsonschema


class Conjunction(jsl.Document):
    terms = jsl.ArrayField(jsl.DocumentField("Term", as_ref=True), required=True)
    type = jsl.StringField(pattern="^and$")


class Disjunction(jsl.Document):
    terms = jsl.ArrayField(jsl.DocumentField("Term", as_ref=True), required=True)
    type = jsl.StringField(pattern="^or$")


class Literal(jsl.Document):
    variable = jsl.StringField(required=True)
    key = jsl.ArrayField(jsl.StringField(), required=False)


class Term(jsl.Document):

    content = jsl.OneOfField([
        jsl.DocumentField(Conjunction, as_ref=True),
        jsl.DocumentField(Disjunction, as_ref=True),
        jsl.DocumentField(Literal, as_ref=True)
    ], required=True)


def __get_schema():
    return Term.get_schema()


def validate_term(json):
    return jsonschema.validate(json,__get_schema())

demo_schema = {
    'content' : {
        'variable' : 'participate',
        'key' : '2'
    }
}
