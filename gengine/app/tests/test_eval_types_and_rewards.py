import datetime
import pytz

from gengine.app.cache import clear_all_caches
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_user, create_achievement, create_variable, create_value, create_goals, create_achievement_rewards, create_achievement_user, create_goal_evaluation_cache
from gengine.metadata import DBSession
from gengine.app.model import Achievement, AchievementUser, Value, t_values
from gengine.base.model import update_connection

class TestAchievementEvaluationTypeAndRewards(BaseDBTest):

    def test_multiple_users_achievemnt_reward(self):

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

        print(achievement.evaluation_timezone)
        achievement_date1 = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement.evaluation)
        print("Achievement date for first user:")
        print(achievement_date1)

        create_achievement_user(user1, achievement, achievement_date1, level=1)
        create_achievement_user(user2, achievement, achievement_date1, level=1)
        create_achievement_user(user3, achievement, achievement_date1, level=1)
        create_achievement_user(user4, achievement, achievement_date1, level=1)

        create_variable("invite_users", variable_group="day")
        Value.increase_value(variable_name="invite_users", user=user1, value=3, key=None)
        Value.increase_value(variable_name="invite_users", user=user2, value=2, key=None)
        Value.increase_value(variable_name="invite_users", user=user3, value=11, key=None)
        Value.increase_value(variable_name="invite_users", user=user4, value=6, key=None)

        create_goals(achievement,
                     goal_goal="3*level",
                     goal_operator="geq",
                     goal_group_by_key=False
                     )

        clear_all_caches()

        # Evaluate achievement for all users
        achievement1 = Achievement.evaluate(user3, achievement.id, achievement_date1)
        print(achievement1)

        new_date = achievement_date1+datetime.timedelta(7)
        print(new_date)
        next_date = Achievement.get_datetime_for_evaluation_type(achievement.evaluation_timezone, achievement.evaluation, dt=new_date)
        achievement = Achievement.evaluate(user3, achievement.id, next_date)
        print(achievement)
