# -*- coding: utf-8 -*-
from gengine.app.model import Value, Subject, t_subjects, Achievement, AchievementDate, SubjectType
from gengine.app.tests.base import BaseDBTest
from gengine.app.tests.helpers import create_subjecttypes, create_subjects, create_achievements, create_variables, \
    default_dt, last_month
from gengine.metadata import DBSession


class TestAchievement(BaseDBTest):

    def test_ancestors_descendants(self):
        create_subjecttypes()
        create_subjects()

        klaus = DBSession.query(Subject).filter_by(name="Klaus").first()
        clara = DBSession.query(Subject).filter_by(name="Clara").first()
        liam = DBSession.query(Subject).filter_by(name="Liam").first()

        bielefeld = DBSession.query(Subject).filter_by(name="Bielefeld").first()
        paderborn = DBSession.query(Subject).filter_by(name="Paderborn").first()
        germany = DBSession.query(Subject).filter_by(name="Germany").first()
        france = DBSession.query(Subject).filter_by(name="France").first()

        dev_team_bielefeld = DBSession.query(Subject).filter_by(name="Developer Team Bielefeld").first()
        junior_developer = DBSession.query(Subject).filter_by(name="Junior Developer").first()

        user_type = DBSession.query(SubjectType).filter_by(name="User").first()
        team_type = DBSession.query(SubjectType).filter_by(name="Team").first()
        country_type = DBSession.query(SubjectType).filter_by(name="Country").first()

        klaus_ancestors = Subject.get_ancestor_subjects(
            subject_id=klaus.id,
            of_type_id=None,
            from_date=default_dt(),
            to_date=default_dt(),
            whole_time_required=False
        )

        self.assertIn(bielefeld.id, klaus_ancestors.keys())
        self.assertIn(germany.id, klaus_ancestors.keys())
        self.assertIn(dev_team_bielefeld.id, klaus_ancestors.keys())
        self.assertIn(junior_developer.id, klaus_ancestors.keys())
        self.assertNotIn(france.id, klaus_ancestors.keys())

        germany_descendants = Subject.get_descendent_subjects(
            subject_id=germany.id,
            of_type_id=team_type.id,
            from_date=default_dt(),
            to_date=default_dt(),
            whole_time_required=False
        )

        self.assertIn(dev_team_bielefeld.id, germany_descendants.keys())
        self.assertNotIn(klaus.id, germany_descendants.keys())


    def test_simple_invite_users(self):
        create_subjecttypes()
        create_subjects()
        create_variables()
        create_achievements()

        klaus = DBSession.query(Subject).filter_by(name="Klaus").first()
        invite_users_achievement = DBSession.query(Achievement).filter_by(name="invite_users").first()

        # First step: increase by 1, level 1 will not be achieved

        Value.increase_value(
            variable_name="invite_users",
            subject_id=klaus.id,
            value=1,
            key=None,
            at_datetime=default_dt()
        )

        evaluation = Achievement.evaluate(
            compared_subject=klaus,
            achievement_id=invite_users_achievement.id,
            achievement_date=AchievementDate.compute(
                evaluation_timezone=invite_users_achievement.evaluation_timezone,
                evaluation_type=invite_users_achievement.evaluation,
                evaluation_shift=invite_users_achievement.evaluation_shift,
                context_datetime=default_dt()
            ),
            context_subject_id=None,
            execute_triggers=False
        )

        self.assertEqual(evaluation["level"], 0)
        self.assertEqual(evaluation["progress"], 1.0)

        # Now increase by 3, level 1 will achieved, progress 4.0

        Value.increase_value(
            variable_name="invite_users",
            subject_id=klaus.id,
            value=3,
            key=None,
            at_datetime=default_dt()
        )

        evaluation = Achievement.evaluate(
            compared_subject=klaus,
            achievement_id=invite_users_achievement.id,
            achievement_date=AchievementDate.compute(
                evaluation_timezone=invite_users_achievement.evaluation_timezone,
                evaluation_type=invite_users_achievement.evaluation,
                evaluation_shift=invite_users_achievement.evaluation_shift,
                context_datetime=default_dt()
            ),
            context_subject_id=None,
            execute_triggers=False
        )

        self.assertEqual(evaluation["level"], 1)
        self.assertEqual(evaluation["progress"], 4.0)

        # Now lets test the maximum level (100)

        Value.increase_value(
            variable_name="invite_users",
            subject_id=klaus.id,
            value=300,
            key=None,
            at_datetime=default_dt()
        )

        evaluation = Achievement.evaluate(
            compared_subject=klaus,
            achievement_id=invite_users_achievement.id,
            achievement_date=AchievementDate.compute(
                evaluation_timezone=invite_users_achievement.evaluation_timezone,
                evaluation_type=invite_users_achievement.evaluation,
                evaluation_shift=invite_users_achievement.evaluation_shift,
                context_datetime=default_dt()
            ),
            context_subject_id=None,
            execute_triggers=False
        )

        self.assertEqual(evaluation["level"], 100)
        self.assertEqual(evaluation["progress"], 304.0)

    def test_cycling_leaderboard(self):

        create_subjecttypes()
        create_subjects()
        create_variables()
        create_achievements()

        klaus = DBSession.query(Subject).filter_by(name="Klaus").first()
        clara = DBSession.query(Subject).filter_by(name="Clara").first()
        liam = DBSession.query(Subject).filter_by(name="Liam").first()

        bielefeld = DBSession.query(Subject).filter_by(name="Bielefeld").first()
        paderborn = DBSession.query(Subject).filter_by(name="Paderborn").first()
        germany = DBSession.query(Subject).filter_by(name="Germany").first()
        france = DBSession.query(Subject).filter_by(name="France").first()

        cyclist_of_the_month_achievement = DBSession.query(Achievement).filter_by(name="cyclist_of_the_month").first()

        def cycle(user, km, dt):
            Value.increase_value(
                variable_name="cycling",
                subject_id=user.id,
                value=km,
                key=None,
                at_datetime=dt
            )

        def ev(user, dt, context_subject):
            return Achievement.evaluate(
                compared_subject=user,
                achievement_id=cyclist_of_the_month_achievement.id,
                achievement_date=AchievementDate.compute(
                    evaluation_timezone=cyclist_of_the_month_achievement.evaluation_timezone,
                    evaluation_type=cyclist_of_the_month_achievement.evaluation,
                    evaluation_shift=cyclist_of_the_month_achievement.evaluation_shift,
                    context_datetime=dt
                ),
                execute_triggers=False,
                context_subject_id=context_subject.id
            )

        cycle(klaus, 5, default_dt())
        cycle(clara, 3, default_dt())
        cycle(liam, 10, default_dt())

        lb_bielefeld = ev(klaus, default_dt(), bielefeld)
        lb_germany = ev(klaus, default_dt(), germany)

        self.assertEqual(lb_bielefeld["leaderboard_position"], 0)
        self.assertEqual(lb_germany["leaderboard_position"], 1)

        lb_bielefeld = ev(clara, default_dt(), bielefeld)
        lb_germany = ev(clara, default_dt(), germany)
        lb_france = ev(clara, default_dt(), france)

        self.assertEqual(lb_bielefeld["leaderboard_position"], 1)
        self.assertEqual(lb_germany["leaderboard_position"], 2)
        self.assertEqual(lb_france["leaderboard_position"], None)

        # clara also cycled last month
        Subject.join_subject(subject_id=clara.id, part_of_id=germany.id, join_date=last_month(default_dt()))
        cycle(clara, 10, last_month(default_dt()))

        # should not effect this month
        lb_germany = ev(clara, default_dt(), germany)
        self.assertEqual(lb_germany["leaderboard_position"], 2)

        # but should effect last month
        lb_germany = ev(clara, last_month(default_dt()), germany)
        self.assertEqual(lb_germany["leaderboard_position"], 0)

