from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_goals, create_goal_properties, create_goal_evaluation_cache
from gengine.app.model import Achievement, User,  Goal, Value


class TestEvaluateGoal(BaseDBTest):
    def test_compute_progress(self):

        user = create_user()
        create_variable(variable_name="invite_users", variable_group="day")
        Value.increase_value(variable_name="invite_users", user=user, value=6, key=None)
        Value.increase_value(variable_name="invite_users", user=user, value=7, key=None)

        create_variable(variable_name="participate", variable_group="day")
        Value.increase_value(variable_name="participate", user=user, value=2, key="5")
        Value.increase_value(variable_name="participate", user=user, value=3, key="7")
        Value.increase_value(variable_name="participate", user=user, value=5, key="7")

        achievement = create_achievement(achievement_name="invite_users_achievement")
        goal = create_goals(achievement)

        # goal is for invite_users, its group_by_key is false, progress is sum of all the values
        achievement_date = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement["evaluation"])
        users_progress_goal = Goal.compute_progress(goal=goal, achievement=achievement, user=user, evaluation_date=achievement_date)
        goal_evaluation = {e["user_id"]: e["value"] for e in users_progress_goal}
        print(goal_evaluation)

        self.assertLessEqual(goal_evaluation.get(user.id), 13)

        # For goal1, since its group_by_key is True, it'll add the values of the same key
        achievement1 = create_achievement(achievement_name="participate_achievement")
        goal1 = create_goals(achievement1)
        achievement_date1= Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement1["evaluation"])
        users_progress_goal1 = Goal.compute_progress(goal=goal1, achievement=achievement1, user=user, evaluation_date=achievement_date1)
        goal_evaluation1 = {e["user_id"]: e["value"] for e in users_progress_goal1}
        print(goal_evaluation1)

        self.assertLess(goal_evaluation1.get(user.id), 10)

        # Check with group_by_key for goals participate = False
        goal2 = create_goals(achievement1, goal_group_by_key=False)
        users_progress_goal1 = Goal.compute_progress(goal=goal2, achievement=achievement1, user=user, evaluation_date=achievement_date1)
        goal_evaluation2 = {e["user_id"]: e["value"] for e in users_progress_goal1}
        print(goal_evaluation2)
        self.assertLessEqual(goal_evaluation2.get(user.id), 10)

    def test_evaluate_goal(self):

        user = create_user()
        create_variable(variable_name="invite_users", variable_group="day")
        Value.increase_value(variable_name="invite_users", user=user, value=6, key=None)
        Value.increase_value(variable_name="invite_users", user=user, value=7, key=None)

        create_variable(variable_name="participate", variable_group="day")
        Value.increase_value(variable_name="participate", user=user, value=6, key="5")
        Value.increase_value(variable_name="participate", user=user, value=3, key="7")
        Value.increase_value(variable_name="participate", user=user, value=5, key="7")

        # Goal Participate with group_by = False
        achievement = create_achievement(achievement_name="participate_achievement")
        goal = create_goals(achievement, goal_group_by_key=False, goal_goal="3*level")
        achievement_date = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement["evaluation"])

        evaluation_result = Goal.evaluate(goal, achievement, achievement_date, user, level=4, goal_eval_cache_before=False, execute_triggers=True)
        print(evaluation_result)
        # True cases
        self.assertGreaterEqual(evaluation_result["value"], 12)
        self.assertEqual(evaluation_result["achieved"], True)

        # Goal Participate with group_by = True
        goal2 = create_goals(achievement, goal_group_by_key=True, goal_goal="3*level")
        evaluation_result2 = Goal.evaluate(goal2, achievement, achievement_date, user, level=4, goal_eval_cache_before=False, execute_triggers=True)
        print(evaluation_result2)

        self.assertLessEqual(evaluation_result2["value"], 12)
        self.assertEqual(evaluation_result2["achieved"], False)

        # Goal invite_users
        achievement1 = create_achievement(achievement_name="invite_users_achievement")
        goal1 = create_goals(achievement1, goal_goal="4*level")
        achievement_date1 = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement1["evaluation"])

        evaluation_result1 = Goal.evaluate(goal1, achievement1, achievement_date1, user, level=2, goal_eval_cache_before=False, execute_triggers=True)
        print(evaluation_result1)

        self.assertGreaterEqual(evaluation_result1["value"], 8)
        self.assertEqual(evaluation_result1["achieved"], True)

    def test_get_goal_properties(self):

        achievement = create_achievement()
        goals = create_goals(achievement)

        create_goal_properties(goals.id)
        level = 4
        result = Goal.get_goal_properties(goals.id, level)
        print(result)

        level1 = 1
        result1 = Goal.get_goal_properties(goals.id, level1)
        print(result1)

        self.assertIsNot(result, [])
        self.assertEquals(result1, [])

    def test_get_leaderboard(self):

        achievement = create_achievement(achievement_name="invite_users_achievement")
        goals = create_goals(achievement)

        # Create multiple users for a goal
        user1 = create_user()
        user2 = create_user(
            lat=85.59,
            lng=65.75,
            country="USA",
            region="Lethal crosside",
            city="New York",
            timezone="US/Eastern",
            language="en",
            additional_public_data={
                "first_name": "Michael",
                "last_name": "Clarke"
            }
        )

        # Create Third user
        user3 = create_user(
            lat=12.1,
            lng=12.2,
            country="RO",
            region="Transylvania",
            city="Cluj-Napoca",
            timezone="Europe/Bucharest",
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
            timezone="Australia/Sydney",
            language="en",
            additional_public_data={
                "first_name": "Steve",
                "last_name": "Waugh"
            },
            friends=[3]
        )

        achievement_date_for_user1 = Achievement.get_datetime_for_evaluation_type(User.get_user(user1.id)["timezone"], achievement["evaluation"])
        achievement_date_for_user2 = Achievement.get_datetime_for_evaluation_type(User.get_user(user2.id)["timezone"], achievement["evaluation"])
        achievement_date_for_user3 = Achievement.get_datetime_for_evaluation_type(User.get_user(user3.id)["timezone"], achievement["evaluation"])
        achievement_date_for_user4 = Achievement.get_datetime_for_evaluation_type(User.get_user(user4.id)["timezone"], achievement["evaluation"])
        print(achievement_date_for_user4)

        create_goal_evaluation_cache(goal_id=goals.id, gec_achievement_date=achievement_date_for_user1, gec_user_id=user1.id, gec_value=22.00, gec_achieved=True)
        create_goal_evaluation_cache(goal_id=goals.id, gec_achievement_date=achievement_date_for_user2, gec_user_id=user2.id, gec_value=8.00, gec_achieved=True)
        create_goal_evaluation_cache(goal_id=goals.id, gec_achievement_date=achievement_date_for_user3, gec_user_id=user3.id, gec_value=15.00, gec_achieved=True)

        # Test for finding leaderboard in case where goal has been evaluated for all given users

        # First get list of friends (user_ids) of given user
        user_ids = Achievement.get_relevant_users_by_achievement_and_user(achievement, user3.id)

        # Get leaderboard
        positions = Goal.get_leaderboard(goals, achievement_date_for_user3, user_ids)
        print(positions)
        self.assertEqual(positions[0]["value"], 22.00)
        self.assertEqual(positions[1]["value"], 15.00)
        self.assertEqual(positions[2]["value"], 8.00)

        # Test for Goal is not evaluated for few user_ids
        create_variable(variable_name="invite_users", variable_group="day")
        Value.increase_value(variable_name="invite_users", user=user4, value=6, key=None)
        Value.increase_value(variable_name="invite_users", user=user4, value=9, key=None)

        user_ids = Achievement.get_relevant_users_by_achievement_and_user(achievement, user4.id)
        positions = Goal.get_leaderboard(goals, achievement_date_for_user4, user_ids)

        print(positions)
        self.assertEqual(positions[0]["value"], 15.00)
