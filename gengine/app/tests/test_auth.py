from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, update_user, delete_user, get_or_create_language
from gengine.metadata import DBSession
from gengine.app.model import User


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
        lang = get_or_create_language("en")
        user = create_user()

        total_rows = DBSession.query(User).count()
        
        user = delete_user(
            user_id = user.id,
        )
        #diff = total_rows - total_rows_after_delete
  
        #self.assertTrue(diff == 1)
        self.assertEqual(user, None)






        