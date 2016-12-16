from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_device, update_device
from gengine.metadata import DBSession
from gengine.app.model import Variable, Value, Achievement, t_variables
from gengine.base.model import ABase, exists_by_expr, datetime_trunc, calc_distance, coords, update_connection


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
        return
        user = create_user()

        variable = Variable()
        variable.name = "participate"
        variable.group = "none"
        DBSession.add(variable)
        print(variable)
        DBSession.flush()

        value = Value()
        value.user_id = user.id
        value.variable_id = variable.id
        value.value = 1
        value.key = "5"
        DBSession.add(value)
        DBSession.flush()

        new_value = value.increase_value(variable.name, user, value.value, value.key)

        # Works correctly when removed check for datetime otherwise failed
        self.assertNotEqual(value.value, new_value)

    def test_get_achievements_by_location(self):
        user = create_user()
        achievement = Achievement()
        achievement.name = "invite_users"
        achievement.valid_start = "2016-12-16"
        achievement.valid_end = "2016-12-18"
        achievement.lat = 40.983
        achievement.lng = 41.562
        achievement.max_distance = 200000
        achievement.evaluation = "immediately"
        achievement.relevance = "own"
        achievement.view_permission = "everyone"
        DBSession.add(achievement)
        DBSession.flush()
        result = achievement.get_achievements_by_user_for_today(user)
        print(result)

        # Works when removed goal condition from achievements_by_location and achievements_by_date
        self.assertNotEqual(result, None)

        #Need to check by adding goal






















