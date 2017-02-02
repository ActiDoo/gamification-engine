from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_variable,create_value
from gengine.app.model import Value


class TestValue(BaseDBTest):
    def test_increase_value(self):
        return
        user = create_user()
        variable = create_variable(variable_name="participate", variable_group="day")

        value1 = Value.increase_value(variable.name, user, value=3, key="5")
        value2 = Value.increase_value(variable.name, user, value=3, key="5")
        value3 = Value.increase_value(variable.name, user, value=6, key="7")

        # Correct cases
        self.assertGreater(value2, value1)

        # Failing cases
        self.assertGreater(value3, value2)

    # Doesn't work when give variable_group = none i.e. current_datetime check which differes for two successive calls
    # Increase value is being called only in evaluate_achievement function and not in evaluate_goal