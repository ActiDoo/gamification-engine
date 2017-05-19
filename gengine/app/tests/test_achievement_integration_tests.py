import datetime

import pytz
from gengine.app.cache import clear_all_caches
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_goals, create_achievement_user
from gengine.app.model import Achievement, Value


class TestAchievementEvaluationType(BaseDBTest):

    # Case1: Achieved in first and next week
    def test_evaluate_achievement_for_weekly_evaluation_case1(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)
        next_weekdate = achievement_date + datetime.timedelta(10)
        print(next_weekdate)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # User has achieved in first week and 2nd week
        print("Weekly evaluation Case 1")
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="weekly", dt=next_weekdate)

        Value.increase_value(variable_name="invite_users", user=user, value=16, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print(achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertNotEqual(next_weekdate, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result["levels_achieved"])
        self.assertIn('3', achievement_result["levels_achieved"])
        self.assertIn('1', achievement_result1["new_levels"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case2: NOT Achieved in first week but in next week
    def test_evaluate_achievement_for_weekly_evaluation_case2(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        next_weekdate = achievement_date + datetime.timedelta(11)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # User has not achieved in first week but in 2nd week
        print("Weekly evaluation Case 2")
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="weekly", dt=next_weekdate)
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertNotEqual(next_weekdate, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('1', achievement_result1["new_levels"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case3: NOT Achieved in first week but after some days in same week
    def test_evaluate_achievement_for_weekly_evaluation_case3(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # User has not achieved in first week and achieved after few days in a same week
        print("Weekly evaluation Case 3")
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="weekly", dt=achievement_date+datetime.timedelta(3))
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertEqual(achievement_date, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case1: Achieved in first and next month
    def test_evaluate_achievement_for_monthly_evaluation_case1(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)
        next_month = achievement_date + datetime.timedelta(35)
        print(next_month)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # User has achieved in this month and next month
        print("Monthly evaluation Case 1")

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="monthly", dt=next_month)

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertNotEqual(next_month, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result["levels_achieved"])
        self.assertIn('3', achievement_result["levels_achieved"])
        self.assertIn('1', achievement_result1["new_levels"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case2: Not achieved in first but in next month
    def test_evaluate_achievement_for_monthly_evaluation_case2(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)
        next_month = achievement_date + datetime.timedelta(31)
        print(next_month)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # User has NOT achieved in this month but in the next month
        print("Monthly evaluation Case 2")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="monthly", dt=next_month+datetime.timedelta(days=10))

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertGreaterEqual(next_month, next_date) # next_month can be the 1st, 2nd, 3rd of 4th (February)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('1', achievement_result1["new_levels"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case3: Achieved in first month and after some days in a same month
    def test_evaluate_achievement_for_monthly_evaluation_case3(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # Not achieved in first month after some days in the same month
        print("Monthly evaluation Case 3")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="monthly", dt=achievement_date+datetime.timedelta(10))
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertEqual(achievement_date, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case1: Achieved in first year and next year
    def test_evaluate_achievement_for_yearly_evaluation_case1(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(425)
        print(next_year)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # Goal achieved in both this month and next year
        print("Yearly evaluation Case 1")

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="yearly", dt=next_year)

        Value.increase_value(variable_name="invite_users", user=user, value=15, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print(achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertNotEqual(next_year, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result["levels_achieved"])
        self.assertIn('3', achievement_result["levels_achieved"])
        self.assertIn('1', achievement_result1["new_levels"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case2: Not Achieved in first year but in next year
    def test_evaluate_achievement_for_yearly_evaluation_case2(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(534)
        print(next_year)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # Not achieved in first year but in the second year
        print("Yearly evaluation Case 2")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="yearly", dt=next_year + datetime.timedelta(10))

        Value.increase_value(variable_name="invite_users", user=user, value=15, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertNotEqual(next_year, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('1', achievement_result1["new_levels"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case3: Achieved in this year and after some days in same year
    def test_evaluate_achievement_for_yearly_evaluation_case3(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement["evaluation"])
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(501)
        print(next_year)

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # Not achieved in first month after some days in the same year
        print("Yearly evaluation Case 3")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, evaluation_type="yearly", dt=achievement_date + datetime.timedelta(110))

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertEqual(achievement_date, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])

    # Case1:
    def test_evaluate_achievement_for_weekly_evaluation_with_shift_case1(self):
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly",
                                         achievement_evaluation_timezone="Europe/Berlin",
                                         achievement_evaluation_shift=-60*60*24*2)

        user = create_user(timezone="Europe/Berlin")

        tz = pytz.timezone(user.timezone)

        achievement_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone,
                                                                        achievement["evaluation"],
                                                                        dt=tz.localize(datetime.datetime(year=2017, month=10, day=31, hour=3)),
                                                                        evaluation_shift=achievement["evaluation_shift"])

        create_achievement_user(user, achievement, achievement_date, level=1)

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
             goal_goal="3*level",
             goal_operator="geq",
             goal_group_by_key=False
        )
        clear_all_caches()

        # User has not achieved in first week and achieved after few days in a same week
        print("Weekly evaluation Case 3")
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None, at_datetime=achievement_date)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone,
                                                                 evaluation_type="weekly",
                                                                 dt=achievement_date + datetime.timedelta(3),
                                                                 evaluation_shift=achievement["evaluation_shift"])
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

        self.assertEqual(achievement_result["achievement_date"], achievement_date)
        self.assertEqual(achievement_result1["achievement_date"], next_date)
        self.assertEqual(achievement_date, next_date)
        self.assertIn('1', achievement_result["levels_achieved"])
        self.assertIn('2', achievement_result1["new_levels"])
        self.assertIn('3', achievement_result1["new_levels"])