import datetime
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_value, create_goals
from gengine.metadata import DBSession
from gengine.app.model import Achievement, User, AchievementUser, Goal, Value, AchievementReward, Reward, AchievementProperty, AchievementAchievementProperty, t_achievements_users
from gengine.base.model import update_connection


class TestAchievement(BaseDBTest):
    # Includes get_achievement_by_location and get_achievement_by_date
    def test_get_achievements_by_location_and_date(self):

        user = create_user()
        achievement1 = create_achievement(achievement_name="invite_users_achievement")
        achievement2 = create_achievement(achievement_name="participate_achievement")
        DBSession.flush()
        create_goals(achievement1)
        achievement_today = Achievement.get_achievements_by_user_for_today(user)
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

        self.assertNotIn(1, friendsOfuser1)
        self.assertNotIn(2, friendsOfuser1)
        self.assertNotIn(4, friendsOfuser3)
        self.assertNotIn(2, friendsOfuser3)
        self.assertNotIn(3, friendsOfuser4)
        self.assertNotIn(2, friendsOfuser4)

        # For the relevance global
        achievement1 = create_achievement(achievement_relevance = "global")
        DBSession.add(achievement1)

        friendsOfuser1 = achievement.get_relevant_users_by_achievement_and_user(achievement1, user3.id)

        self.assertNotIn(1, friendsOfuser1)

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

        user = create_user(timezone="US/Eastern", country="USA", region="xyz", city="New York")

        achievement = create_achievement(achievement_name="invite_users_achievement")

        achievement_date = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement["evaluation"])

        achievement_users = AchievementUser()
        achievement_users.user_id = user.id
        achievement_users.achievement_id = achievement["id"]
        achievement_users.achievement_date = achievement_date
        achievement_users.level = 2
        DBSession.add(achievement_users)
        DBSession.flush()

        level_object = achievement.get_level(user.id, achievement["id"], achievement_date)
        level = achievement.get_level_int(user.id, achievement.id, achievement_date)

        achievement_monthly = create_achievement(achievement_evaluation="weekly")

        achievement_date1 = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement_monthly["evaluation"])
        print("achievemnt date")
        print(achievement_date1)

        level_object1 = achievement.get_level(user.id, achievement["id"], achievement_date1)

        # Test for get_level as integer
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

        # passed test cases
        self.assertNotEqual(rewardlist2, None)
        self.assertNotEqual(rewardlist3, None)

        # failed test cases
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
        print(result1)

        result2 = Achievement.get_achievement_properties(achievement.id, 1)
        print(result2)

        self.assertNotEqual(result1, [])
        self.assertNotEqual(result2, [])

    def test_evaluate_achievement_for_participate(self):
        return
        achievement = create_achievement(achievement_name="participate_achievement", achievement_relevance="own", achievement_maxlevel=4)

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])

        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        variable = create_variable("participate", "none")
        Value.increase_value(variable_name=variable.name, user=user, value=1, key="5")

        goal = create_goals(achievement,
                            goal_condition="""{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate"}}""",
                            goal_group_by_key=True,
                            goal_operator="geq",
                            goal_goal="1*level")

        level = Achievement.evaluate(user, achievement.id, achievement_date).get("level")
        print("level ",level)
        result1 = Value.increase_value(variable_name="participate", user=user, value=5, key="5")
        print("value result ",result1)
        level2 = Achievement.evaluate(user, achievement.id, achievement_date)
        print("level2 ",level2)
        result2 = Value.increase_value(variable_name="participate", user=user, value=1, key="5")
        # result3 = Value.increase_value(variable_name="participate", user=user, value=1, key="5")
        # result = Achievement.evaluate(user, achievement.id, achievement_date)

        #self.assertEqual(result["level"], achievement.maxlevel)

    def test_evaluate_achievement_for_invite_users(self):
        return
        # increase_value function: may need to remove time-constraint, because difference of millisecond fail to increase the value next time
        # Achievement with relevance friends and maxlevel 3
        achievement = create_achievement(achievement_relevance="friends", achievement_maxlevel=3)

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])

        # get level
        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        variable = create_variable("invite_users", "none")
        firstvalue = Value.increase_value(variable_name="invite_users", user=user, value=1, key="5")
        print("firstvalue ", firstvalue)
        DBSession.flush()

        goal = Goal()
        goal.condition = """{"term": {"type": "literal", "variable": "invite_users"}}"""
        goal.goal = "3*level"
        goal.operator = "geq"
        goal.group_by_key = False
        goal.achievement_id = achievement.id
        DBSession.add(goal)
        DBSession.flush()

        level = Achievement.evaluate(user, achievement.id, achievement_date).get("level")
        print("level ",level)
        new2 = Value.increase_value(variable_name="invite_users", user=user, value=8, key="5")
        print("new2 ",new2)
        level2 = Achievement.evaluate(user, achievement.id, achievement_date)
        new = Value.increase_value(variable.name, user, 7, key="5")
        print("level2 ", level2)
        x = Goal.evaluate(goal,achievement,achievement_date, user.id, Achievement.evaluate(user, achievement.id, achievement_date).get("level"))
        print("goal eval",x)
        level3 = Achievement.evaluate(user, achievement.id, achievement_date)
        print("level3 ",level3)

    def test_get_reward_and_properties_for_achievement(self):
        return
        user = create_user()

        achievement = create_achievement(achievement_name="invite_users_achievement", achievement_relevance="friends", achievement_maxlevel=3)

        # Check for property
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

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])

        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        variable = create_variable("invite_users", "none")
        firstvalue = Value.increase_value(variable_name="invite_users", user=user, value=2, key="5")
        DBSession.flush()

        goal = create_goals(achievement = achievement,
                            goal_condition="""{"term": {"type": "literal", "variable": "invite_users"}}""",
                            goal_group_by_key=True,
                            goal_operator="geq",
                            goal_goal="1*level")

        result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(result)

        self.assertNotEqual(len(result["new_levels"]["2"]["rewards"]), 0)

        Value.increase_value(variable_name="invite_users", user=user, value=2, key="5")
        DBSession.flush()

        # result = Achievement.evaluate(user, achievement.id, achievement_date)
        # print(result)

        # result1 = Achievement.get_achievement_properties(achievement.id, 4)
        # print("in test property",result1)

        self.assertNotEqual(len(result["new_levels"]["2"]["properties"]), 0)

    def test_multiple_goals_of_same_achievement(self):
        return
        user = create_user()

        achievement = create_achievement(achievement_name="participate_achievement", achievement_maxlevel=3)

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

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])

        goal1 = create_goals(achievement=achievement,
                             goal_condition="""{"term": {"key": ["5","7"], "type": "literal", "key_operator": "IN", "variable": "participate_seminar"}}""",
                             goal_group_by_key=False,
                             goal_operator="geq",
                             goal_goal="2*level",
                             goal_name = "goal_participate_seminar")

        goal2 = create_goals(achievement=achievement,
                             goal_condition="""{"term": {"type": "literal", "variable": "participate_talk"}}""",
                             goal_group_by_key=False,
                             goal_operator="geq",
                             goal_goal="1*level",
                             goal_name="goal_participate_talk")

        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        variable1 = create_variable("participate_seminar",variable_group=None)
        variable2 = create_variable("participate_talk", variable_group=None)
        Value.increase_value(variable1.name, user, "2", "5")
        Value.increase_value(variable1.name, user, "2", "7")
        Value.increase_value(variable2.name, user, "2", key=None)

        result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(result)
        Value.increase_value(variable1.name, user, "2", "7")
        result1 = Achievement.evaluate(user, achievement.id, achievement_date)
        print(result1)
        Value.increase_value(variable2.name, user, "2", key=None)
        result2 = Achievement.evaluate(user, achievement.id, achievement_date)
        print(result2)

        self.assertNotEqual(len(result["new_levels"]["2"]["rewards"]), 0)