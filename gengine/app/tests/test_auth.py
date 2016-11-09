from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user


class TestUserCreation(BaseDBTest):
    def test_user_creation(self):
        user = create_user()
        self.assertTrue(user.country == "DE")
