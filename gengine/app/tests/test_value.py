from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_variable,create_value
from gengine.app.model import Value


class TestValue(BaseDBTest):
    def test_increase_value(self):
        user = create_user()
        variable = create_variable("participate", "none")
        key = "5"
        value = create_value(user.id, variable.id, 1, key)

        value1 = Value.increase_value(variable.name, user, 3, key)
        value2 = Value.increase_value(variable.name, user, 2, key)

        self.assertGreater(value2, value1)

    # Problems in increase_value function. May be because datetime check.
    # Increase value is being called only in evaluate_achievement function and not in evaluate_goal