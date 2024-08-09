from dataclasses import dataclass


@dataclass
class CreateVisit:
    """
    Dataclass wrapping the parameters for an automated visit creation (in the `Visit_Windows`
    table). If no visit should be created, `None` should be used instead of an instance of this
    class.
    """

    project_id: int
    cohort_id:  int
