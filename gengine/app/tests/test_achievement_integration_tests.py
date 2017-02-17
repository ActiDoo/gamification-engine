import datetime
import pytz

from gengine.app.cache import clear_all_caches
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_value, create_goals, create_achievement_rewards, create_achievement_user
from gengine.metadata import DBSession
from gengine.app.model import Achievement, AchievementUser, Value, t_values
from gengine.base.model import update_connection

class TestAchievementEvaluationType(BaseDBTest):

    # Case1: Achieved in first and next week
    def test_evaluate_achievement_for_weekly_evaluation_case1(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print(achievement_date)
        next_weekdate = achievement_date + datetime.timedelta(7)
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
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="weekly", dt=next_weekdate)

        Value.increase_value(variable_name="invite_users", user=user, value=16, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print(achievement_result1)


    # Case2: NOT Achieved in first week but in next week
    def test_evaluate_achievement_for_weekly_evaluation_case2(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        next_weekdate = achievement_date + datetime.timedelta(7)

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
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result2 = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result2)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="weekly", dt=next_weekdate+datetime.timedelta(3))
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_resul1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_resul1)

    # Case3: NOT Achieved in first week but after some days in same week
    def test_evaluate_achievement_for_weekly_evaluation_case3(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])

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
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="weekly", dt=achievement_date+datetime.timedelta(3))
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_resul1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_resul1)

    # Case1: Achieved in first and next month
    def test_evaluate_achievement_for_monthly_evaluation_case1(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print(achievement_date)
        next_month = achievement_date + datetime.timedelta(28)
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

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="monthly", dt=next_month)

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_resul1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_resul1)

    # Case2: Not achieved in first but in next month
    def test_evaluate_achievement_for_monthly_evaluation_case2(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print(achievement_date)
        next_month = achievement_date + datetime.timedelta(28)
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

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="monthly", dt=next_month+datetime.timedelta(10))

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

    # Case2: Achieved in first month and after some days in a same month
    def test_evaluate_achievement_for_monthly_evaluation_case3(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
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

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="monthly", dt=achievement_date+datetime.timedelta(10))
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

    # Case1: Achieved in first year and next year
    def test_evaluate_achievement_for_yearly_evaluation_case1(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(365)
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

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="yearly", dt=next_year)

        Value.increase_value(variable_name="invite_users", user=user, value=15, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print(achievement_result1)

    # Case2: Not Achieved in first year but in next year
    def test_evaluate_achievement_for_yearly_evaluation_case2(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(365)
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

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="yearly", dt=next_year + datetime.timedelta(10))

        Value.increase_value(variable_name="invite_users", user=user, value=15, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)

    # Case3: Achieved in this year and after some days in same year
    def test_evaluate_achievement_for_yearly_evaluation_case3(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(365)
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

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        next_date = Achievement.get_datetime_for_evaluation_type(tz=user.timezone, evaluation_type="yearly", dt=achievement_date + datetime.timedelta(110))

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None, at_datetime=next_date)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_date)
        print("achievement result1: ", achievement_result1)