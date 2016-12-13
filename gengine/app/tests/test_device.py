from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_device, update_device
from gengine.metadata import DBSession
from gengine.app.model import Variable, Value, t_values
from sqlalchemy import (and_, select)


class TestUserDevice(BaseDBTest):
    def test_create_user_device(self):
        return
        user = create_user()

        device = create_device(
            device_id='3424',
            user_id=user.id,
            device_os='Android',
            push_id='1234',
            app_version='1.1'
        )

        self.assertTrue(device.device_id == '3424')
        self.assertTrue(device.user_id == user.id)
        self.assertTrue(device.device_os == 'Android')
        self.assertTrue(device.push_id == '1234')
        self.assertTrue(device.app_version == '1.1')

    def test_update_user_device(self):
        return
        user = create_user()
        create_device(user_id=user.id)

        device = update_device(
            user_id=user.id,
            device_id='1256',
            push_id='5126',
            device_os='iOS',
            app_version='1.2'
        )

        self.assertTrue(device.device_id == '1256')
        self.assertTrue(device.user_id == user.id)
        self.assertTrue(device.device_os == 'iOS')
        self.assertTrue(device.push_id == '5126')
        self.assertTrue(device.app_version == '1.2')

    def test_map_variables_to_rules(self):
        return
        map1 = Variable.map_variables_to_rules()
        print(map1)
        self.assertNotEqual(map1, None)

    def test_invalidate_caches_for_variable_and_user(self):
        return
        variable_id = 1,
        user_id = 1
        Variable.invalidate_caches_for_variable_and_user(variable_id, user_id)

        goalsandachievements = Variable.map_variables_to_rules().get(variable_id,[])

        self.assertEqual(goalsandachievements, None)

    def test_increase_value(self):
        variable_name = "participate"
        user = create_user()

        variable = Variable()
        variable.id = 1
        variable.name = "participate"
        DBSession.add(variable)

        value = 2
        key = 5

        tz = user["timezone"]
        variable = Variable.get_variable_by_name(variable_name)
        print(variable["id"])

        condition = and_(
                         t_values.c.variable_id == variable["id"],
                         t_values.c.user_id == user.id,
                         t_values.c.key == str(key))

        current_value = DBSession.execute(select([t_values.c.value, ]).where(condition)).scalar()
        print(current_value)

        Value.increase_value(variable_name, user, value, key, at_datetime=None)

        new_value = DBSession.execute(select([t_values.c.value, ]).where(condition)).scalar()
        print(new_value)

        self.assertNotEqual(current_value, new_value)























