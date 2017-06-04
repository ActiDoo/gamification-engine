# -*- coding: utf-8 -*-
import datetime
import pytz

from gengine.app.cache import clear_all_caches
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_goals, create_achievement_rewards, create_achievement_user
from gengine.metadata import DBSession
from gengine.app.model import Achievement, User, AchievementSubject, Value, AchievementReward, Reward, AchievementProperty, AchievementAchievementProperty, t_values
from gengine.base.model import update_connection

class TestAchievement(BaseDBTest):

    # Includes get_achievement_by_location and get_achievement_by_date
    def test_get_achievements_by_location_and_date(self):

        user = create_user()
        achievement1 = create_achievement(achievement_name="invite_users_achievement")
        achievement2 = create_achievement(achievement_name="participate_achievement")
        create_goals(achievement1)
        create_goals(achievement2)
        achievement_today = Achievement.get_achievements_by_user_for_today(user)
        print("achievement_today")
        print(achievement_today)

        self.assertEqual(achievement_today[0]["name"], "invite_users_achievement")
        self.assertEqual(len(achievement_today), 2)

    def test_get_relevant_users_by_achievement_friends_and_user(self):

        #Create First user
        user1 = create_user()

        # Create Second user
        user2 = create_user(
            lat = 85.59,
            lng = 65.75,
            country = "DE",
            region = "Niedersachsen",
            city = "Osnabrück",
            timezone = "Europe/Berlin",
            language = "de",
            additional_public_data = {
                "first_name" : "Michael",
                "last_name" : "Clarke"
            }
        )

        # Create Third user
        user3 = create_user(
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
            },
            friends=[1, 2]
        )

        # Create Fourth user
        user4 = create_user(
            lat = 25.56,
            lng = 15.89,
            country = "AU",
            region = "Sydney",
            city = "New South Wales",
            timezone = "Australia",
            language = "en",
            additional_public_data = {
                "first_name" : "Steve",
                "last_name" : "Waugh"
            },
            friends=[3]
        )

        achievement = create_achievement()
        friendsOfuser1 = achievement.get_relevant_users_by_achievement_and_user(achievement, user1.id)
        friendsOfuser3 = achievement.get_relevant_users_by_achievement_and_user(achievement, user3.id)
        friendsOfuser4 = achievement.get_relevant_users_by_achievement_and_user(achievement, user4.id)

        self.assertIn(1, friendsOfuser1)
        self.assertIn(1, friendsOfuser3)
        self.assertIn(2, friendsOfuser3)
        self.assertIn(3, friendsOfuser4)

        # For the relevance global
        achievement1 = create_achievement(achievement_relevance = "global")

        friendsOfuser1 = achievement.get_relevant_users_by_achievement_and_user(achievement1, user3.id)

        self.assertIn(1, friendsOfuser1)
        self.assertIn(2, friendsOfuser1)
        self.assertIn(3, friendsOfuser1)
        self.assertIn(4, friendsOfuser1)

    def test_get_relevant_users_by_achievement_friends_and_user_reverse(self):

        # Create First user
        user1 = create_user()

        # Create Second user
        user2 = create_user(
            lat=85.59,
            lng=65.75,
            country="DE",
            region="Niedersachsen",
            city="Osnabrück",
            timezone="Europe/Berlin",
            language="de",
            additional_public_data={
                "first_name": "Michael",
                "last_name": "Clarke"
            },
            friends = [user1.id]
        )

        # Create Third user
        user3 = create_user(
            lat=12.1,
            lng=12.2,
            country="RO",
            region="Transylvania",
            city="Cluj-Napoca",
            timezone="Europe/Bukarest",
            language="en",
            additional_public_data={
                "first_name": "Rudolf",
                "last_name": "Red Nose"
            },
            friends=[user1.id, user2.id]
        )

        # Create Fourth user
        user4 = create_user(
            lat=25.56,
            lng=15.89,
            country="AU",
            region="Sydney",
            city="New South Wales",
            timezone="Australia",
            language="en",
            additional_public_data={
                "first_name": "Steve",
                "last_name": "Waugh"
            },
            friends=[user2.id, user3.id]
        )

        achievement = create_achievement()
        usersForFriend1 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user1.id)
        usersForFriend2 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user2.id)
        usersForFriend3 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user3.id)
        usersForFriend4 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user4.id)

        self.assertIn(user2.id, usersForFriend1)
        self.assertIn(user3.id, usersForFriend1)
        self.assertIn(user3.id, usersForFriend2)
        self.assertIn(user4.id, usersForFriend2)
        self.assertIn(user4.id, usersForFriend3)
        self.assertIn(user4.id, usersForFriend4)

    def test_get_level(self):

        user = create_user(timezone="Australia/Sydney", country="Australia", region="xyz", city="Sydney")
        achievement = create_achievement(achievement_name="invite_users_achievement", achievement_evaluation="weekly")

        achievement_date = Achievement.get_datetime_for_evaluation_type(evaluation_timezone=achievement.evaluation_timezone, evaluation_type="weekly")

        create_achievement_user(user, achievement, achievement_date, level=2)

        achievement.get_level(user.id, achievement["id"], achievement_date)
        level = achievement.get_level_int(user.id, achievement.id, achievement_date)

        achievement_date1 = Achievement.get_datetime_for_evaluation_type(evaluation_timezone=achievement.evaluation_timezone, evaluation_type="weekly", dt=achievement_date + datetime.timedelta(7))

        achievement.get_level(user.id, achievement["id"], achievement_date1)
        level1 = achievement.get_level_int(user.id, achievement.id, achievement_date1)

        # Test for get_level as integer
        print("level1:", level1)
        self.assertEqual(level, 2)
        self.assertEqual(level1, 0)

    def test_get_rewards(self):

        achievement = create_achievement(achievement_maxlevel=3)
        create_achievement_rewards(achievement)
        clear_all_caches()
        rewardlist1 = Achievement.get_rewards(achievement.id, 1)
        print("rewardlist1",rewardlist1)

        rewardlist2 = Achievement.get_rewards(achievement.id, 5)
        print("rewardlist2", rewardlist2)

        rewardlist3 = Achievement.get_rewards(achievement.id, 3)
        print("rewardlist3", rewardlist3)

        self.assertEqual(rewardlist1, [])
        self.assertEqual(rewardlist2, [])
        self.assertNotEqual(rewardlist3, [])

    def test_get_achievement_properties(self):

        achievement = create_achievement(achievement_maxlevel=3)

        achievementproperty = AchievementProperty()
        achievementproperty.name = "xp"
        DBSession.add(achievementproperty)
        DBSession.flush()

        achievements_achievementproperty = AchievementAchievementProperty()
        achievements_achievementproperty.achievement_id = achievement.id
        achievements_achievementproperty.property_id = achievementproperty.id
        achievements_achievementproperty.value = "5"
        achievements_achievementproperty.from_level = 2
        DBSession.add(achievements_achievementproperty)
        DBSession.flush()

        clear_all_caches()

        result1 = Achievement.get_achievement_properties(achievement.id, 4)
        print(result1)

        result2 = Achievement.get_achievement_properties(achievement.id, 1)
        print(result2)

        self.assertNotEqual(result1, [])
        self.assertEqual(result2, [])

    def test_evaluate_achievement_for_participate(self):

        achievement = create_achievement(achievement_name="participate_achievement", achievement_relevance="own", achievement_maxlevel=4)

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement.evaluation)

        current_level = 1
        achievement_user = AchievementSubject()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        variable = create_variable("participate", variable_group="day")
        Value.increase_value(variable_name=variable.name, user=user, value=1, key="5")

        create_goals(achievement,
                     goal_condition="""{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate"}}""",
                     goal_group_by_key=True,
                     goal_operator="geq",
                     goal_goal="1*level")

        clear_all_caches()

        level = Achievement.evaluate(user, achievement.id, achievement_date).get("level")

        Value.increase_value(variable_name="participate", user=user, value=1, key="7", at_datetime=achievement_date)
        level2 = Achievement.evaluate(user, achievement.id, achievement_date).get("level")

        Value.increase_value(variable_name="participate", user=user, value=5, key="5", at_datetime=achievement_date)
        level1 = Achievement.evaluate(user, achievement.id, achievement_date).get("level")

        self.assertEqual(level, 1)
        self.assertEqual(level2, 1)
        self.assertEqual(level1, 4)

    def test_evaluate_achievement_for_invite_users(self):

        achievement = create_achievement(achievement_name="invite_users_achievement", achievement_relevance="friends", achievement_maxlevel=10)

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement.evaluation)

        create_achievement_user(user=user, achievement=achievement, achievement_date=achievement_date, level=1)

        update_connection().execute(t_values.delete())
        create_variable("invite_users", variable_group="day")
        Value.increase_value(variable_name="invite_users", user=user, value=1, key=None, at_datetime=achievement_date)

        create_goals(achievement,
                     goal_goal="1*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        level = Achievement.evaluate(user, achievement.id, achievement_date).get("level")
        print("level: ", level)

        Value.increase_value(variable_name="invite_users", user=user, value=8, key=None, at_datetime=achievement_date)
        level1 = Achievement.evaluate(user, achievement.id, achievement_date).get("level")
        print("level1 ", level1)

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        level2 = Achievement.evaluate(user, achievement.id, achievement_date).get("level")
        print("level2: ", level2)

        self.assertEqual(level, 1)
        self.assertEqual(level1, 9)
        self.assertEqual(level2, 10)

    def test_get_reward_and_properties_for_achievement(self):

        user = create_user()

        achievement = create_achievement(achievement_name="invite_users_achievement", achievement_relevance="friends", achievement_maxlevel=3)

        achievementproperty = AchievementProperty()
        achievementproperty.name = "xp"
        DBSession.add(achievementproperty)
        DBSession.flush()

        achievements_achievementproperty = AchievementAchievementProperty()
        achievements_achievementproperty.achievement_id = achievement.id
        achievements_achievementproperty.property_id = achievementproperty.id
        achievements_achievementproperty.value = "5"
        achievements_achievementproperty.from_level = None
        DBSession.add(achievements_achievementproperty)
        DBSession.flush()

        create_achievement_rewards(achievement=achievement)

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement.evaluation)

        create_achievement_user(user=user, achievement=achievement, achievement_date=achievement_date, level=1)

        create_variable("invite_users", "none")
        Value.increase_value(variable_name="invite_users", user=user, value=4, key="5", at_datetime=achievement_date)

        create_goals(achievement = achievement,
                     goal_condition="""{"term": {"type": "literal", "variable": "invite_users"}}""",
                     goal_group_by_key=True,
                     goal_operator="geq",
                     goal_goal="1*level")

        clear_all_caches()
        result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("reward_achievement_result:",result)

        self.assertEqual(len(result["new_levels"]["2"]["rewards"]), 0)
        self.assertEqual(len(result["new_levels"]["3"]["rewards"]), 1)
        self.assertEqual(len(result["new_levels"]["2"]["properties"]), 1)
        self.assertEqual(len(result["new_levels"]["3"]["properties"]), 1)

    def test_multiple_goals_of_same_achievement(self):

        user = create_user()

        achievement = create_achievement(achievement_name="participate_achievement", achievement_maxlevel=3)

        create_achievement_rewards(achievement=achievement)

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement.evaluation)

        create_goals(achievement=achievement,
                     goal_condition="""{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate_seminar"}}""",
                     goal_group_by_key=False,
                     goal_operator="geq",
                     goal_goal="2*level",
                     goal_name = "goal_participate_seminar")

        create_goals(achievement=achievement,
                     goal_condition="""{"term": {"type": "literal", "variable": "participate_talk"}}""",
                     goal_group_by_key=False,
                     goal_operator="geq",
                     goal_goal="1*level",
                     goal_name="goal_participate_talk")

        clear_all_caches()
        create_achievement_user(user=user, achievement=achievement, achievement_date=achievement_date, level=1)

        variable1 = create_variable("participate_seminar", variable_group=None)
        variable2 = create_variable("participate_talk", variable_group=None)
        Value.increase_value(variable1.name, user, "2", "5", at_datetime=achievement_date)
        Value.increase_value(variable1.name, user, "3", "7", at_datetime=achievement_date)
        Value.increase_value(variable2.name, user, "3", key=None, at_datetime=achievement_date)

        result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("multiple_goals_of_same_achievement:",result)
        Value.increase_value(variable1.name, user, "2", "7", at_datetime=achievement_date)
        result1 = Achievement.evaluate(user, achievement.id, achievement_date)
        print(result1)
        Value.increase_value(variable2.name, user, "2", key=None, at_datetime=achievement_date)
        result2 = Achievement.evaluate(user, achievement.id, achievement_date)
        print(result2)

        self.assertEqual(len(result["levels"]["3"]["rewards"]), 1)
        self.assertEqual(result["levels"]["1"]["goals"]["1"]["goal_goal"], 2)
        self.assertEqual(result["levels"]["3"]["goals"]["2"]["goal_goal"], 3)
        self.assertEqual(result1["levels"]["2"]["goals"]["1"]["goal_goal"], 4)
        self.assertEqual(result1["levels"]["3"]["goals"]["2"]["goal_goal"], 3)
        self.assertEqual(result2["levels"]["2"]["goals"]["1"]["goal_goal"], 4)
        self.assertEqual(result2["levels"]["3"]["goals"]["2"]["goal_goal"], 3)

