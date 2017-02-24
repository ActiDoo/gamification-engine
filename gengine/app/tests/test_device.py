from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_device, update_device


class TestUserDevice(BaseDBTest):

    def test_create_user_device(self):

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

        user = create_user()
        create_device(user_id=user.id)

        device = update_device(
            user_id=user.id,
            device_id='1256',
            push_id='5126',
            device_os='iOS',
            app_version='1.2'
        )

        # Correct cases
        self.assertTrue(device.device_id == '1256')
        self.assertTrue(device.user_id == user.id)
        self.assertTrue(device.push_id == '5126')
        self.assertTrue(device.app_version == '1.2')

























