import datetime
import pytz

from gengine.app.cache import clear_all_caches
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_value, create_goals, create_achievement_rewards, create_achievement_user
from gengine.metadata import DBSession
from gengine.app.model import Achievement, AchievementUser, Value, t_values
from gengine.base.model import update_connection

class TestAchievementEvaluationTypeAndRewards(BaseDBTest):

    def test_multiple_users_achievemnt_reward(self):
        return
        user1 = create_user()

        # Create Second user
        user2 = create_user(
            lat=85.59,
            lng=65.75,
            country="DE",
            region="Roland",
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

        achievement = create_achievement(achievement_name="invite_users_achievement",
                                         achievement_relevance="friends",
                                         achievement_maxlevel=3,
                                         achievement_evaluation="weekly")

        achievement_date1 = Achievement.get_datetime_for_evaluation_type(user1["timezone"], achievement["evaluation"])
        print("Achievement date for first user:")
        print(achievement_date1)
        create_achievement_user(user1, achievement, achievement_date1, level=1)
        achievement_date2 = Achievement.get_datetime_for_evaluation_type(user2["timezone"], achievement["evaluation"])
        print("Achievement date for second user:")
        print(achievement_date2)
        create_achievement_user(user2, achievement, achievement_date2, level=1)
        achievement_date3 = Achievement.get_datetime_for_evaluation_type(user3["timezone"], achievement["evaluation"])
        create_achievement_user(user3, achievement, achievement_date3, level=1)
        achievement_date4 = Achievement.get_datetime_for_evaluation_type(user4["timezone"], achievement["evaluation"])
        create_achievement_user(user4, achievement, achievement_date4, level=1)

        create_variable("invite_users", variable_group="day")
        Value.increase_value(variable_name="invite_users", user=user1, value=3, key=None)
        Value.increase_value(variable_name="invite_users", user=user2, value=2, key=None)
        Value.increase_value(variable_name="invite_users", user=user3, value=1, key=None)
        Value.increase_value(variable_name="invite_users", user=user4, value=6, key=None)

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )

        clear_all_caches()

        # Evaluate achievement for all users
        achievement1 = Achievement.evaluate(user1, achievement.id, achievement_date1)
        print(achievement1)
        achievement2 = Achievement.evaluate(user2, achievement.id, achievement_date2)
        print(achievement2)
        achievement3 = Achievement.evaluate(user3, achievement.id, achievement_date3)
        print(achievement3)
        achievement4 = Achievement.evaluate(user4, achievement.id, achievement_date4)
        print(achievement4)

        Value.increase_value(variable_name="invite_users", user=user1, value=6, key=None)
        Value.increase_value(variable_name="invite_users", user=user2, value=5, key=None)
        # Value.increase_value(variable_name="invite_users", user=user3, value=8, key=None)
        # Value.increase_value(variable_name="invite_users", user=user4, value=2, key=None)
        #
        # print("In the next week for all users")
        # achievement1_1 = Achievement.evaluate(user1, achievement.id, achievement_date1+datetime.timedelta(7))
        # print(achievement1_1)
        # achievement2_1 = Achievement.evaluate(user2, achievement.id, achievement_date2+datetime.timedelta(7))
        # print(achievement2_1)
        # achievement3_1 = Achievement.evaluate(user3, achievement.id, achievement_date3+datetime.timedelta(7))
        # print(achievement3_1)
        # achievement4_1 = Achievement.evaluate(user4, achievement.id, achievement_date4+datetime.timedelta(7))
        # print(achievement4_1)