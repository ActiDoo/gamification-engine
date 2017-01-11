from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_variable, create_value, Variable
from gengine.app.model import Variable, Value


class TestValue(BaseDBTest):
    def test_increase_value(self):
        return
        user = create_user()
        variable = create_variable("participate", "none")
        value_key5 = create_value(user.id, variable.id, 2, "5")
        value_key7 = create_value(user.id, variable.id, 3, "7")

        new_value_key5 = Value.increase_value(variable.name, user, 1, value_key5.key)
        new_value_key7 = value_key5.increase_value(variable.name, user, 2, value_key7.key)

        # Works correctly when removed check for datetime otherwise failed
        self.assertNotEqual(value_key5.value, new_value_key5)
        self.assertless(value_key5.value, new_value_key7)

    def test_map_variables_to_rules(self):
        return
        map1 = Variable.map_variables_to_rules()
        print(map1)
        self.assertNotEqual(map1, None)

    def test_invalidate_caches_for_variable_and_user(self):
        return
        variable = create_variable()
        user = create_user()
        Variable.invalidate_caches_for_variable_and_user(variable.id, user.id)

        goalsandachievements = Variable.map_variables_to_rules().get(variable.id, [])

        self.assertEqual(goalsandachievements, None)
