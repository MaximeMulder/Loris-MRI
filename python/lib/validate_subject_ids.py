from lib.database import Database
from lib.database_lib.candidate_db import CandidateDB
from lib.database_lib.visit_windows import VisitWindows
from lib.dataclass.create_visit import CreateVisit
from lib.dataclass.subject import Subject
from lib.exception.validate_subject_exception import ValidateSubjectException


def validate_subject_ids(db: Database, verbose: bool, subject: Subject, create_visit: CreateVisit | None):
    """
    Validate a subject's information against the database from its parts (PSCID, CandID, VisitLabel).
    Raise an exception if an error is found, or return `None` otherwise.
    """

    candidate_db = CandidateDB(db, verbose)
    candidate_psc_id = candidate_db.get_candidate_psc_id(subject.cand_id)
    if candidate_psc_id is None:
        validate_subject_error(
            subject,
            f'Candidate (CandID = \'{subject.cand_id}\') does not exist in the database.'
        )

    if candidate_psc_id != subject.psc_id:
        validate_subject_error(
            subject,
            f'Candidate (CandID = \'{subject.cand_id}\') PSCID does not match the subject PSCID.\n'
            f'Candidate PSCID = \'{candidate_psc_id}\', Subject PSCID = \'{subject.psc_id}\''
        )

    visit_window_db = VisitWindows(db, verbose)
    visit_window_exists = visit_window_db.check_visit_label_exists(subject.visit_label)
    if not visit_window_exists and create_visit is not None:
        validate_subject_error(
            subject,
            f'Visit label \'{subject.visit_label}\' does not exist in the database (table `Visit_Windows`).'
        )


def validate_subject_error(subject: Subject, message: str):
    raise ValidateSubjectException(f'Validation error for subject \'{subject.name}\'.\n{message}')
