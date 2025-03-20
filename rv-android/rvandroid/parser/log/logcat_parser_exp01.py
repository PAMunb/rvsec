# rvandroid/parser/log/logcat_parser_exp01.py

"""
Legacy logcat parser refactored to use the standardized LogcatRepository.
This parser is maintained for backward compatibility but now uses the same
data structures as the modern parser.
"""

from rvandroid.model.coverage import LogcatRepository
from rvandroid.model.log import RvErrorLog, RvCoverageLog


def to_error(s: str) -> RvErrorLog:
    """
    Parse an error log line into an RvErrorLog object.

    Args:
        s: Error log line text

    Returns:
        RvErrorLog object
    """
    if "FSM" in s:
        split = s.split(":::")
        tmp = split[0]
        tmp = tmp[:tmp.find("(")]
        dot_idx = tmp.rfind(".")
        clazz = tmp[:dot_idx]
        method = tmp[dot_idx + 1:]
        message = split[1].strip()
        spec = message.split(" ")[0]
        return RvErrorLog(spec, spec, clazz, method, "Unknown Source:1", message)
    else:
        split = s.split(",")
        spec = split[0]
        clazz = split[1]
        # clazz_name = split[2]
        method = split[3]
        source = split[4]
        error_type = split[5]
        msg_idx = find_sixth_comma(s)
        message = s[msg_idx + 1:].strip()
        return RvErrorLog(spec, error_type, clazz, method, source, message)


def find_sixth_comma(text: str) -> int:
    """
    Find the position of the sixth comma in a text.

    Args:
        text: Text to search in

    Returns:
        Position of the sixth comma or -1 if not found
    """
    idx = -1
    for _ in range(6):
        idx = text.find(',', idx + 1)
        if idx == -1:
            break
    return idx


def parse_logcat_file(log_file: str) -> LogcatRepository:
    """
    Parse a logcat file and return a standardized LogcatRepository.

    This method has been refactored to use the standardized repository model
    while maintaining the same parsing logic for backward compatibility.

    Args:
        log_file: Path to the logcat file

    Returns:
        LogcatRepository with parsed data
    """
    # Initialize the repository
    repository = LogcatRepository()

    # Track handled errors to avoid duplicates
    handled_errors = set()

    with open(log_file) as f:
        while True:
            line = f.readline()
            if not line:
                break
            tag, right_term = __get_tag(line)
            match tag:
                case "RVSEC":
                    error = to_error(right_term)
                    if error.unique_msg in handled_errors:
                        continue
                    handled_errors.add(error.unique_msg)
                    # Add to repository instead of a separate list
                    repository.register_error(error)
                case "RVSEC-COV":
                    cov = __cov_method_sig(right_term)
                    # Add to repository instead of a dictionary
                    repository.register_method_call(cov)

    return repository


def parse_logcat_file_legacy_format(log_file: str):
    """
    Legacy version of parse_logcat_file that returns the old format.
    This is maintained only for backward compatibility.

    Args:
        log_file: Path to the logcat file

    Returns:
        Tuple of (errors, called_methods, ordered_methods)
    """
    repository = parse_logcat_file(log_file)

    # For backward compatibility, convert repository data to old format
    errors = []
    for class_data in repository.classes.values():
        for method_data in class_data.methods.values():
            if method_data.called:
                # Reconstruct old format data
                pass

    # This is a stub - in the actual implementation, we would:
    # 1. Extract all errors from repository.errors
    # 2. Build the called_methods dictionary
    # 3. Create an ordered list of methods
    # But we're encouraging migration to the repository model instead

    logger = logging.getLogger(__name__)
    logger.warning("Using legacy parse_logcat_file_legacy_format - consider migrating to repository-based API")

    # For simplicity, just parse the file again using the old method
    # In a real implementation, we would convert from the repository data
    from rvandroid.parser.log.logcat_parser_exp01_legacy import parse_logcat_file as legacy_parse
    return legacy_parse(log_file)


def __get_tag(line: str):
    """
    Extract the tag and content from a logcat line.

    Args:
        line: Logcat line

    Returns:
        Tuple of (tag, content)
    """
    tag = ""
    text = ""

    if ":" in line:
        idx = line.index(":")
        tag = line[2:idx].strip()
        text = line[idx + 1:].strip()

    return tag, text


def __cov_method_sig(text: str) -> RvCoverageLog:
    """
    Parse a coverage log line into an RvCoverageLog object.

    Args:
        text: Coverage log line

    Returns:
        RvCoverageLog object
    """
    sp = text.split(":::")

    clazz = sp[0].strip()
    method = sp[1].strip()
    params = sp[2].strip() if len(sp) > 2 else ""

    return RvCoverageLog(clazz, method, params)
