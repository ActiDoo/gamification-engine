from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, update_user, delete_user, get_or_create_language
from gengine.metadata import DBSession
from gengine.app.model import User, AuthUser


class TestUserCreation(BaseDBTest):
    def test_user_creation(self):
        return
        lang = get_or_create_language("en")

        user = create_user(
            lat = 12.1,
            lng = 12.2,
            country = "RO",
            region = "Transylvania",
            city = "Cluj-Napoca",
            timezone = "Europe/Bukarest",
            language = "en",
            additional_public_data = {
                "first_name" : "Rudolf",
                "last_name" : "Red Nose"
            }
        )

        self.assertTrue(user.lat == 12.1)
        self.assertTrue(user.lng == 12.2)
        self.assertTrue(user.country == "RO")
        self.assertTrue(user.region == "Transylvania")
        self.assertTrue(user.city == "Cluj-Napoca")
        self.assertTrue(user.timezone == "Europe/Bukarest")
        self.assertTrue(user.language_id == lang.id)
        self.assertTrue(user.additional_public_data["first_name"] == "Rudolf")
        self.assertTrue(user.additional_public_data["last_name"] == "Red Nose")

    def test_user_updation(self):
        return
        lang = get_or_create_language("en")
        user = create_user()
        user = update_user(
            user_id = user.id,
            lat = 14.2,
            lng = 16.3,
            country = "EN",
            region = "Transylvania",
            city = "Cluj-Napoca",
            timezone = "Europe/Bukarest",
            language = "en",
            additional_public_data = {
                "first_name" : "Rudolf",
                "last_name" : "Red Nose"
            }
        )
  
        self.assertTrue(user.lat == 14.2)
        self.assertTrue(user.lng == 16.3)
        self.assertTrue(user.country == "EN")
        self.assertTrue(user.region == "Transylvania")
        self.assertTrue(user.city == "Cluj-Napoca")
        self.assertTrue(user.timezone == "Europe/Bukarest")
        self.assertTrue(user.language_id == lang.id)
        self.assertTrue(user.additional_public_data["first_name"] == "Rudolf")
        self.assertTrue(user.additional_public_data["last_name"] == "Red Nose")

    def test_user_deletion(self):
        return
        lang = get_or_create_language("en")
        user = create_user()

        user = delete_user(
            user_id = user.id
        )

        self.assertE(user, None)

    def test_verify_password(self):
        return
        auth_user = AuthUser()
        auth_user.password = "test12345"
        auth_user.active = True
        auth_user.email = "test@actidoo.com"
        DBSession.add(auth_user)

        iscorrect = auth_user.verify_password("test12345")
        print(isCorrect)

        self.assertEqual(iscorrect, True)

    def test_create_token(self):
        return
        user = create_user()
        auth_user = AuthUser()
        auth_user.user_id = user.id
        auth_user.password = "test12345"
        auth_user.active = True
        auth_user.email = "test@actidoo.com"
        DBSession.add(auth_user)

        if auth_user.verify_password("test12345"):
            token = auth_user.get_or_create_token()

        print(token)
        self.assertNotEqual(token, None)





