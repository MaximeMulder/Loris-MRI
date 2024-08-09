from dataclasses import dataclass


@dataclass
class Subject:
    """
    Dataclass wrapping information about a (non-phantom) subject.
    """

    name: str
    # The name of the subject may be either the DICOM's PatientName or PatientID depending on the
    # LORIS configuration.
    is_phantom:  bool
    # For a phantom scan, the PSCID and CandID are those of the scanner.
    psc_id:      str
    cand_id:     int
    visit_label: str
