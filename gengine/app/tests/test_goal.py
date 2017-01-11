from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_value, create_goals, create_goal_properties
from gengine.metadata import DBSession
from gengine.app.model import Achievement, User,  Goal, GoalEvaluationCache


class TestEvaluateGoal(BaseDBTest):
    def test_compute_progress(self):
        return
        achievement = create_achievement()
        goals = create_goals(achievement)
        user = create_user()

        variable_participate = create_variable("participate", "none")
        create_value(user.id, variable_participate.id, 2, "5")
        create_value(user.id, variable_participate.id, 3, "7")
        create_value(user.id, variable_participate.id, 5, "7")

        variable_invite = create_variable("invite_users", "none")
        create_value(user.id, variable_invite.id, 6)
        create_value(user.id, variable_invite.id, 7)

        # For goal0, since its group_by_key is false, progress is sum of all the values of Keys 5 and 7
        users_progress_goal0 = Goal.compute_progress(goals[0], achievement, user.id)
        goal0_evaluation = {e["user_id"]: e["value"] for e in users_progress_goal0}
        print(goal0_evaluation)

        # For goal1, since its group_by_key is True, it'll group by key and add their respective values
        users_progress_goal1 = Goal.compute_progress(goals[1], achievement, user.id)
        goal1_evaluation = {e["user_id"]: e["value"] for e in users_progress_goal1}
        print(goal1_evaluation)

        self.assertLessEqual(goal0_evaluation.get(user.id), 13)

        # Check with group_by_key for goals[1] = False
        self.assertLessEqual(goal1_evaluation.get(user.id), 10)

        # Check with group_by_key for goals[1] = True
        self.assertLessEqual(goal1_evaluation.get(user.id), 2)

        # If group_by_key attribute for goal is not set, then default value is considered as False and NOT None
        # In compute_progress function , group_by_key is compared with None. Is it desired or need to change it to False?


    def test_evaluate_goal(self):
        return
        achievement = create_achievement()
        goal = create_goals(achievement)
        user = create_user()
        achievement_date = Achievement.get_datetime_for_evaluation_type(User.get_user(user.id)["timezone"], achievement["evaluation"])

        evaluation_result = Goal.evaluate(goal[0], achievement, achievement_date, user.id, 5, goal_eval_cache_before=False, execute_triggers=True)
        print(evaluation_result)
        evaluation_result1 = Goal.evaluate(goal[1], achievement, achievement_date, user.id, 2, goal_eval_cache_before=False, execute_triggers=True)
        print(evaluation_result1)

        # True cases
        self.assertLessEqual(evaluation_result["value"], 25.0)
        self.assertEqual(evaluation_result["achieved"], True)

        # False cases
        self.assertGreater(evaluation_result1["value"], 0.0)
        self.assertEqual(evaluation_result1["achieved"], True)


    def test_execute_triggers(self):
        return
        # Function is called inside evaluate_goal function
        achievement = create_achievement()
        goal = create_goals(achievement)
        user = create_user()
        print(goal[0])
        level = 5
        previous_goal = Goal.basic_goal_output(goal[0], level - 1).get("goal_goal", 0)
        print(previous_goal)
        current_goal = Goal.basic_goal_output(goal[0], level).get("goal_goal", 0)
        print(current_goal)

        # What is "value" here?
        # We are considering parameter value as 0
        value = 0.0
        result = Goal.select_and_execute_triggers(goal[1], user.id, level, current_goal, value, previous_goal)
        print(result)  # None
        # What is expected result?


    def test_get_goal_properties(self):
        return
        achievement = create_achievement()
        goals = create_goals(achievement)

        create_goal_properties(goals[0].id)

        level = 4
        result = Goal.get_goal_properties(goals[0].id, level)
        print(result)

        level1 = 1
        result1 = Goal.get_goal_properties(goals[0].id, level1)
        print(result1)

        # True test
        self.assertIsNotNone(result)

        # False test
        #  self.assertNotEqual(result1, [])


    def test_get_leaderboard(self):
        return
        achievement = create_achievement()
        goals = create_goals(achievement)

        # Create multiple users for a goal
        user1 = create_user()
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

        # Creating entries for goal_evaluation_cache
        goal_evaluation_cache = GoalEvaluationCache()
        goal_evaluation_cache.goal_id = goals[0].id
        goal_evaluation_cache.achievement_date = achievement_date_for_user1
        goal_evaluation_cache.user_id = user1.id
        goal_evaluation_cache.achieved = True
        goal_evaluation_cache.value = 8.00
        DBSession.add(goal_evaluation_cache)
        DBSession.flush()

        goal_evaluation_cache = GoalEvaluationCache()
        goal_evaluation_cache.goal_id = goals[0].id
        goal_evaluation_cache.achievement_date = achievement_date_for_user2
        goal_evaluation_cache.user_id = user2.id
        goal_evaluation_cache.achieved = True
        goal_evaluation_cache.value = 6.00
        DBSession.add(goal_evaluation_cache)
        DBSession.flush()

        # Test for finding leaderboard in case where goal has been evaluated for all given users

        # First get list of friends (user_ids) of given user
        user_ids = Achievement.get_relevant_users_by_achievement_and_user(achievement, user3.id)

        # Get leaderboard
        positions = Goal.get_leaderboard(goals[0], achievement_date_for_user3, user_ids)

        self.assertEqual(positions[1]["user"]["additional_public_data"]["last_name"], "Clarke")
        self.assertEqual(positions[0]["value"], 8.00)

        # Test for Goal is not evaluated for few user_ids
        user_ids = Achievement.get_relevant_users_by_achievement_and_user(achievement, user4.id)
        positions = Goal.get_leaderboard(goals[0], achievement_date_for_user4, user_ids)

        print(positions)
        self.assertEqual(positions[0]["value"], 8.00)
        self.assertEqual(positions[1]["user"]["additional_public_data"]["last_name"], "Clarke")