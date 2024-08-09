from dataclasses import dataclass

from python.lib.dataclass.create_visit import CreateVisit
from python.lib.dataclass.subject import Subject


@dataclass
class SubjectConfig:
    """
    Dataclass wrapping structured information about the config returned by the `get_subject_ids`
    function of the Python LORIS-MRI config file.
    """

    subject: Subject
    create_visit: CreateVisit | None
