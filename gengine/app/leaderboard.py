from gengine.base.util import dt_now
from sqlalchemy.sql.expression import select, and_, or_

from gengine.app.model import t_subjects, t_subjectrelations, t_subjects_subjects, Subject
from gengine.metadata import DBSession

import logging
# TODO: ADD date filter (compare created_at)
# TODO: filter deleted


class GlobalLeaderBoardSubjectSet:

    @classmethod
    def forward(cls, subjecttype_id, from_date, to_date, whole_time_required):
        q = select([t_subjects.c.id, ]).where(t_subjects.c.subjecttype_id == subjecttype_id)
        if from_date != None and to_date != None:
            if whole_time_required:
                q = q.where(and_(
                    t_subjects.c.created_at <= from_date
                    #or_(
                    #    t_subjects.c.deleted_at == None,
                    #    t_subjects.c.deleted_at >= to_date
                    #)
                ))
            else:
                q = q.where(or_(
                    and_(
                        t_subjects.c.created_at <= from_date,
                        #or_(
                        #    t_subjects.c.deleted_at >= from_date,
                        #    t_subjects.c.deleted_at == None,
                        #)
                    ),
                    and_(
                        t_subjects.c.created_at >= from_date,
                        t_subjects.c.created_at <= to_date,
                    )
                ))
        return [x.id for x in DBSession.execute(q).fetchall()]

    #@classmethod
    #def reverse(cls):
    #    return cls.forward()


class RelationsLeaderBoardSubjectSet:

    @classmethod
    def forward(cls, subject_id, from_date, to_date, whole_time_required):
        subjects = [subject_id, ]

        q = select([t_subjectrelations.c.to_id, ], t_subjectrelations.c.from_id == subject_id)

        if from_date and to_date:
            if whole_time_required:
                q = q.where(and_(
                    t_subjectrelations.c.created_at <= from_date,
                    or_(
                        t_subjectrelations.c.deleted_at == None,
                        t_subjectrelations.c.deleted_at >= to_date
                    )
                ))
            else:
                q = q.where(or_(
                    and_(
                        t_subjectrelations.c.created_at <= from_date,
                        or_(
                            t_subjectrelations.c.deleted_at >= from_date,
                            t_subjectrelations.c.deleted_at == None,
                        )
                    ),
                    and_(
                        t_subjectrelations.c.created_at >= from_date,
                        t_subjectrelations.c.created_at <= to_date,
                    )
                ))
        else:
            q = q.where(
                t_subjectrelations.c.deleted_at == None,
            )

        subjects += [x["to_id"] for x in DBSession.execute(q).fetchall()]

        return subjects

    #@classmethod
    #def reverse(cls, subject_id):
    #    subjects = [subject_id, ]
    #    subjects += [x["from_id"] for x in DBSession.execute(select([t_subjects_subjects.c.from_id, ], t_subjects_subjects.c.to_id == subject_id)).fetchall()]
    #    return subjects


class ContextSubjectLeaderBoardSubjectSet:

    @classmethod
    def forward(cls, subjecttype_id, context_subject_id, from_date, to_date, whole_time_required=False):
        # We are comparing all subjects of type subject_type which have been part of context_subject_id between from_date and to_date
        # By default, they don't have to be member all the time (whole_time_required).

        #print("Looking for descendents of %s of type %s" % (context_subject_id, subjecttype_id))
        #print("From Date: %s, To Date: %s, whole_time_required: %s" % (from_date, to_date, whole_time_required))

        ancestor_subjects = Subject.get_descendent_subjects(
            subject_id=context_subject_id,
            of_type_id=subjecttype_id,
            from_date=from_date if from_date else dt_now(),
            to_date=to_date if to_date else dt_now(),
            whole_time_required=whole_time_required
        )

        subjects = [x for x in ancestor_subjects.keys()]

        return subjects

    #@classmethod
    #def reverse(cls, subject_type_id, context_subject_id, from_date, to_date):
    #    return cls.forward(subject_type=subject_type_id, context_subject_id=context_subject_id, from_date=from_date, to_date=to_date)
