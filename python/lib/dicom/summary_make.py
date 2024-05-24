from functools import cmp_to_key
import os
import pydicom
import pydicom.errors
from lib.dicom.summary_type import Summary, Info, Patient, Scanner, Acquisition, DicomFile, OtherFile
from lib.dicom.text import make_hash, read_dicom_date_none


def get_value(dicom: pydicom.Dataset, tag: str):
    """
    Get a required value from a DICOM.
    """
    if tag not in dicom:
        raise Exception(f'Expected DICOM tag \'{tag}\' but found none.')

    return dicom[tag].value


def get_value_none(dicom: pydicom.Dataset, tag: str):
    """
    Get a nullable value from a DICOM.
    """
    if tag not in dicom:
        return None

    return dicom[tag].value or None


# Pydicom can return subclasses of primitive types (str, float...), which may
# be incompatible with other libraries. So it is important to cast these values
# back to the base Python type.

def get_value_float(dicom: pydicom.Dataset, tag: str):
    return float(get_value(dicom, tag))


def get_value_int(dicom: pydicom.Dataset, tag: str):
    return int(get_value(dicom, tag))


def get_value_string(dicom: pydicom.Dataset, tag: str):
    return str(get_value(dicom, tag))


def get_value_float_none(dicom: pydicom.Dataset, tag: str):
    value = get_value_none(dicom, tag)
    return float(value) if value is not None else None


def get_value_int_none(dicom: pydicom.Dataset, tag: str):
    value = get_value_none(dicom, tag)
    return int(value) if value is not None else None


def get_value_string_none(dicom: pydicom.Dataset, tag: str):
    value = get_value_none(dicom, tag)
    return str(value) if value is not None else None


def cmp_int_none(a: int | None, b: int | None):
    """
    Order comparison between two nullable integers.
    """
    match a, b:
        case None, None:
            return 0
        case _, None:
            return -1
        case None, _:
            return 1
        case a, b:
            return a - b


def cmp_string_none(a: str | None, b: str | None):
    """
    Order comparison between two nullable strings.
    """
    match a, b:
        case None, None:
            return 0
        case _, None:
            return -1
        case None, _:
            return 1
        case a, b if a < b:
            return -1
        case a, b if a > b:
            return 1
        case a, b:
            return 0


def cmp_files(a: DicomFile, b: DicomFile):
    """
    Compare the order of two files to sort them in the summary.
    """
    return \
        cmp_int_none(a.series_number, b.series_number) or \
        cmp_int_none(a.file_number, b.file_number) or \
        cmp_int_none(a.echo_number, b.echo_number)


def cmp_acquis(a: Acquisition, b: Acquisition):
    """
    Compare the order of two acquisitions to sort them in the summary.
    """
    return \
        a.series_number - b.series_number or \
        cmp_string_none(a.sequence_name, b.sequence_name)


def get_dir_files(prefix: str, path: str) -> list[str]:
    """
    Recursively get the files of a directory.
    """
    if os.path.isdir(prefix + '/' + path):
        files = []
        for file in os.listdir(prefix + '/' + path):
            files += get_dir_files(prefix, path + '/' + file)

        # Flatten the lists of files
        return files

    return [path]

def make(dir_path: str, verbose: bool):
    """
    Create a DICOM summary object from a DICOM directory path.
    """

    info = None
    dicom_files: list[DicomFile] = []
    other_files: list[OtherFile] = []
    acquis_dict: dict[tuple[int, int | None, str | None], Acquisition] = dict()

    file_names = get_dir_files(dir_path, '')
    for i, file_name in enumerate(file_names):
        if verbose:
            print(f'Processing file \'{file_name}\' ({i + 1}/{len(file_names)})')

        try:
            dicom = pydicom.dcmread(dir_path + '/' + file_name)
            if info is None:
                info = make_info(dicom)

            dicom_files.append(make_dicom_file(dicom))

            series   = get_value_int(dicom, 'SeriesNumber')
            echo     = get_value_int_none(dicom, 'EchoNumbers')
            sequence = get_value_string_none(dicom, 'SequenceName')

            if not (series, echo, sequence) in acquis_dict:
                acquis_dict[(series, echo, sequence)] = make_acqui(dicom)

            acquis_dict[(series, echo, sequence)].number_of_files += 1
        except pydicom.errors.InvalidDicomError:
            other_files.append(make_other_file(dir_path + '/' + file_name))

    if info is None:
        raise Exception('Found no DICOM file in the directory.')

    acquis = list(acquis_dict.values())

    dicom_files = sorted(dicom_files, key=cmp_to_key(cmp_files))
    acquis      = sorted(acquis,      key=cmp_to_key(cmp_acquis))

    return Summary(info, acquis, dicom_files, other_files)


def make_info(dicom: pydicom.Dataset):
    """
    Create an `Info` object from a DICOM file, containing general information
    about the DICOM directory.
    """

    birth_date = read_dicom_date_none(get_value_none(dicom, 'PatientBirthDate'))
    scan_date  = read_dicom_date_none(get_value_none(dicom, 'StudyDate'))

    patient = Patient(
        get_value_string(dicom, 'PatientID'),
        get_value_string(dicom, 'PatientName'),
        get_value_string_none(dicom, 'PatientSex'),
        birth_date,
    )

    scanner = Scanner(
        get_value_string(dicom, 'Manufacturer'),
        get_value_string(dicom, 'ManufacturerModelName'),
        get_value_string(dicom, 'DeviceSerialNumber'),
        get_value_string(dicom, 'SoftwareVersions'),
    )

    return Info(
        get_value_string(dicom, 'StudyInstanceUID'),
        patient,
        scanner,
        scan_date,
        get_value_string_none(dicom, 'InstitutionName'),
        get_value_string(dicom, 'Modality'),
    )


def make_dicom_file(dicom: pydicom.Dataset):
    """
    Create a `DicomFile` object from a DICOM file, containing information about
    this DICOM file.
    """
    return DicomFile(
        os.path.basename(dicom.filename),
        make_hash(dicom.filename),
        get_value_int_none(dicom, 'SeriesNumber'),
        get_value_string_none(dicom, 'SeriesInstanceUID'),
        get_value_string_none(dicom, 'SeriesDescription'),
        get_value_int_none(dicom, 'InstanceNumber'),
        get_value_int_none(dicom, 'EchoNumbers'),
        get_value_float_none(dicom, 'EchoTime'),
        get_value_string_none(dicom, 'SequenceName'),
    )


def make_other_file(file_path: str):
    """
    Create an `OtherFile` object from a non-DICOM file, containing information
    about this file.
    """
    return OtherFile(
        os.path.basename(file_path),
        make_hash(file_path),
    )


def make_acqui(dicom: pydicom.Dataset):
    """
    Create an `Acquisition` object from a DICOM file, containg information
    about a DICOM series.
    """
    return Acquisition(
        get_value_int(dicom, 'SeriesNumber'),
        get_value_string_none(dicom, 'SeriesInstanceUID'),
        get_value_string_none(dicom, 'SeriesDescription'),
        get_value_string_none(dicom, 'SequenceName'),
        get_value_float_none(dicom, 'EchoTime'),
        get_value_float_none(dicom, 'RepetitionTime'),
        get_value_float_none(dicom, 'InversionTime'),
        get_value_float_none(dicom, 'SliceThickness'),
        get_value_string_none(dicom, 'InPlanePhaseEncodingDirection'),
        0,
        get_value_string_none(dicom, 'Modality'),
    )
