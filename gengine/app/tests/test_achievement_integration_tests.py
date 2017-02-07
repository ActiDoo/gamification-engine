import datetime
import pytz

from gengine.app.cache import clear_all_caches
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_value, create_goals, create_achievement_rewards
from gengine.metadata import DBSession
from gengine.app.model import Achievement, AchievementUser, Value, t_values
from gengine.base.model import update_connection

class TestAchievementEvaluationType(BaseDBTest):

    def test_evaluate_achievement_for_weekly_evaluation(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print("achievement_date")
        print(achievement_date)
        next_weekdate = achievement_date + datetime.timedelta(7)
        print(next_weekdate)


        # get level
        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # User has not achieved in first week and 2nd week
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ",achievement_result)

        clear_all_caches()
        Value.increase_value(variable_name="invite_users", user=user, value=6, key=None)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_weekdate)
        print(achievement_result1)

        update_connection().execute(t_values.delete())
        DBSession.flush()

        # User has not achieved in first week but in 2nd week
        print("Case 2")
        clear_all_caches()
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result2 = Achievement.evaluate(user, achievement.id, next_weekdate)
        print(achievement_result2)

        clear_all_caches()
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_resul3 = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_resul3)

        update_connection().execute(t_values.delete())
        DBSession.flush()

        # User has not achieved in first week and achieved after few days in a same week
        print("Case 3")
        clear_all_caches()
        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result4 = Achievement.evaluate(user, achievement.id, achievement_date)
        print(achievement_result4)

        clear_all_caches()
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_resul5 = Achievement.evaluate(user, achievement.id, next_weekdate+datetime.timedelta(3))
        print("achievement result: ", achievement_resul5)

        # What should happen if the value increased in a same week? Here its starting over again.

    def test_evaluate_achievement_for_monthly_evaluation(self):

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="monthly")

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print("achievement_date")
        print(achievement_date)
        next_month = achievement_date + datetime.timedelta(28)
        print(next_month)

        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # Goal achieved in both this month and next month
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)
        clear_all_caches()

        achievement_result1 = Achievement.evaluate(user, achievement.id, next_month)
        print(achievement_result1)
        clear_all_caches()

        update_connection().execute(t_values.delete())
        DBSession.flush()

        # Not achieved in first month but in the second month
        print("Test for Not achieved in first but in second month")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result2 = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result2)
        clear_all_caches()

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result3 = Achievement.evaluate(user, achievement.id, next_month)
        print("achievement result: ", achievement_result3)
        clear_all_caches()

        update_connection().execute(t_values.delete())
        DBSession.flush()

        # Not achieved in first month after some days in the same month
        print("Case 3")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result4 = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result4)
        clear_all_caches()

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result5 = Achievement.evaluate(user, achievement.id, achievement_date + datetime.timedelta(15))
        print("achievement result: ", achievement_result5)

        # If we executed first two two cases of this function together then while executing second case,
        # it takes levels from first case i.e. execution of 2nd case is starting from max_level 3 which means cache are not getting cleared even after a call to clear_cache function

    def test_evaluate_achievement_for_yearly_evaluation(self):
        return
        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="yearly")

        reward = create_achievement_rewards(achievement)

        user = create_user()

        achievement_date = Achievement.get_datetime_for_evaluation_type(user["timezone"], achievement["evaluation"])
        print("achievement_date")
        print(achievement_date)
        next_year = achievement_date + datetime.timedelta(365)
        print(next_year)

        current_level = 1
        achievement_user = AchievementUser()
        achievement_user.user_id = user.id
        achievement_user.achievement_id = achievement.id
        achievement_user.achievement_date = achievement_date
        achievement_user.level = current_level
        DBSession.add(achievement_user)
        DBSession.flush()

        create_variable("invite_users", variable_group="day")

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )
        clear_all_caches()

        # Goal achieved in both this month and next year
        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)

        clear_all_caches()
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_year)
        print(achievement_result1)

        update_connection().execute(t_values.delete())
        DBSession.flush()

        # Not achieved in first year but in the second year
        print("Test for Not achieved in first but in second year")

        Value.increase_value(variable_name="invite_users", user=user, value=2, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)
        clear_all_caches()

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result1 = Achievement.evaluate(user, achievement.id, next_year)
        print("achievement result: ", achievement_result1)

        update_connection().execute(t_values.delete())
        DBSession.flush()

        # Not achieved in first month after some days in the same year
        print("Case 3")

        Value.increase_value(variable_name="invite_users", user=user, value=5, key=None)
        achievement_result = Achievement.evaluate(user, achievement.id, achievement_date)
        print("achievement result: ", achievement_result)
        clear_all_caches()

        Value.increase_value(variable_name="invite_users", user=user, value=10, key=None)
        achievement_result1 = Achievement.evaluate(user, achievement.id, achievement_date + datetime.timedelta(215))
        print("achievement result: ", achievement_result1)