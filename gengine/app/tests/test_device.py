from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_device, update_device, create_achievement, create_variable, create_value, create_goals
from gengine.metadata import DBSession
from gengine.app.model import Variable, Value, Achievement, User, t_achievements_users, Reward, AchievementReward, AchievementProperty, AchievementAchievementProperty, Goal
from gengine.base.model import  update_connection


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
        variable = create_variable()
        value = create_value()

        new_value = value.increase_value(variable.name, user, value.value, value.key)

        # Works correctly when removed check for datetime otherwise failed
        self.assertNotEqual(value.value, new_value)

    # Includes get_achievement_by_location and get_achievement_by_date
    def test_get_achievements_by_location(self):
        return
        user = create_user()
        achievement = create_achievement()
        DBSession.flush()
        result = achievement.get_achievements_by_user_for_today(user)
        print(result)

        # Works when removed goal condition from achievements_by_location and achievements_by_date
        self.assertNotEqual(result, None)

        #Need to check by adding goal

    def test_get_relevant_users_by_achievement_friends_and_user(self):
        return
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

        self.assertNotIn(1, friendsOfuser1)
        self.assertNotIn(2, friendsOfuser1)
        self.assertNotIn(4, friendsOfuser3)
        self.assertNotIn(2, friendsOfuser3)
        self.assertNotIn(3, friendsOfuser4)
        self.assertNotIn(2, friendsOfuser4)

        # For the relevance global
        achievement1 = Achievement()
        achievement1.name = "invite_users"
        achievement1.valid_start = "2016-12-16"
        achievement1.valid_end = "2016-12-18"
        achievement1.lat = 40.983
        achievement1.lng = 41.562
        achievement1.max_distance = 200000
        achievement1.evaluation = "immediately"
        achievement1.relevance = "global"
        achievement1.view_permission = "everyone"
        DBSession.add(achievement1)

        friendsOfuser1 = achievement.get_relevant_users_by_achievement_and_user(achievement1, user3.id)

        self.assertNotIn(1, friendsOfuser1)

    def test_get_relevant_users_by_achievement_friends_and_user_reverse(self):
        return
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
            friends = [1]

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
            friends=[1, 2]
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
            friends=[2, 3]
        )

        achievement = create_achievement()
        usersForFriend1 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user1.id)
        usersForFriend2 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user2.id)
        usersForFriend3 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user3.id)
        usersForFriend4 = achievement.get_relevant_users_by_achievement_and_user_reverse(achievement, user4.id)

        print(usersForFriend1)
        print(usersForFriend2)
        print(usersForFriend3)
        print(usersForFriend4)

        self.assertNotIn(4, usersForFriend1)
        self.assertNotIn(2, usersForFriend1)
        self.assertNotIn(1, usersForFriend2)
        self.assertNotIn(3, usersForFriend2)
        self.assertNotIn(1, usersForFriend3)
        self.assertNotIn(4, usersForFriend3)
        self.assertNotIn(2, usersForFriend4)
        self.assertNotIn(4, usersForFriend4)

    def test_get_level(self):
        return
        user = create_user()

        achievement = create_achievement()

        achievement_date = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement["evaluation"])

        update_connection().execute(t_achievements_users.insert().values({
            "user_id": user.id,
            "achievement_id": achievement["id"],
            "achievement_date": achievement_date,
            "level": 1
        }))

        DBSession.flush()

        level_object = achievement.get_level(user.id, achievement["id"], achievement_date)

        # Change achievement date
        achievement_monthly = Achievement()
        achievement_monthly.name = "invite_users"
        achievement_monthly.valid_start = "2016-12-16"
        achievement_monthly.valid_end = "2016-12-18"
        achievement_monthly.lat = 40.983
        achievement_monthly.lng = 41.562
        achievement_monthly.max_distance = 200000
        achievement_monthly.evaluation = "monthly"
        achievement_monthly.relevance = "friends"
        achievement_monthly.view_permission = "everyone"
        DBSession.add(achievement_monthly)
        DBSession.flush()

        achievement_date1 = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement_monthly["evaluation"])

        level_object1 = achievement.get_level(user.id, achievement["id"], achievement_date1)

        # Test for get_level as integer
        level = achievement.get_level_int(user.id, achievement.id, achievement_date)
        level1 = achievement.get_level_int(user.id, achievement.id, achievement_date1)

        # Passed cases
        self.assertNotEqual(level_object, None)
        self.assertEqual(level_object1, [])
        self.assertEqual(level, 1)
        self.assertEqual(level1, 0)

        # Failed cases
        self.assertEqual(level1, 1)
        self.assertEqual(level_object, None)

    def test_get_rewards(self):
        return
        achievement = create_achievement()

        reward = Reward()
        reward.name = "badge"
        DBSession.add(reward)
        DBSession.flush()

        achievement_reward = AchievementReward()
        achievement_reward.achievement_id = achievement.id
        achievement_reward.reward_id = reward.id
        achievement_reward.value = "https://www.gamification-software.com/img/trophy_{level1}.png"
        achievement_reward.from_level = 2
        DBSession.add(achievement_reward)
        DBSession.flush()

        achievement_reward = AchievementReward()
        achievement_reward.achievement_id = achievement.id
        achievement_reward.reward_id = reward.id
        achievement_reward.value = "https://www.gamification-software.com/img/trophy_{level2}.png"
        achievement_reward.from_level = 3
        DBSession.add(achievement_reward)
        DBSession.flush()

        rewardlist1 = Achievement.get_rewards(achievement.id, 1)
        print(rewardlist1)

        rewardlist2 = Achievement.get_rewards(achievement.id, 2)
        print(rewardlist2)

        rewardlist3 = Achievement.get_rewards(achievement.id, 3)
        print(rewardlist3)

        self.assertNotEqual(rewardlist2, None)
        self.assertNotEqual(rewardlist3, None)
        self.assertEqual(rewardlist1, None)

    def test_get_achievement_properties(self):
        return
        achievement = create_achievement()

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

        result1 = Achievement.get_achievement_properties(achievement.id, 4)

        result2 = Achievement.get_achievement_properties(achievement.id, 1)

        self.assertNotEqual(result1, [])
        self.assertNotEqual(result2, [])

    def test_evaluate_achievement(self):
        return

    def test_compute_progress(self):
        goals = create_goals()
        achievement = create_achievement()
        user = create_user()

        result1 = Goal.compute_progress(goals[0], achievement, user.id)
        result2 = Goal.compute_progress(goals[1], achievement, user.id)

        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)

    def test_evaluate_goal(self):
        achievement = create_achievement()
        goal = create_goals()
        user = create_user()
        achievement_date = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement["evaluation"])

        Goal.evaluate(goal, achievement, achievement_date, user.id, 2, goal_eval_cache_before=False,execute_triggers=True)
























