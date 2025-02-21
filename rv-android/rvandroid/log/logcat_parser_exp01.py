from rvandroid.log.log import RvErrorLog, RvCoverageLog


def to_error(s: str):
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


def find_sixth_comma(text: str):
    idx = -1
    for _ in range(6):
        idx = text.find(',', idx + 1)
        if idx == -1:
            break
    return idx


def parse_logcat_file(log_file: str):
    called_methods: dict[str, list[RvCoverageLog]] = {}
    rvsec_errors: list[RvErrorLog] = []
    methods: list[RvCoverageLog] = []

    handled_errors: set[str] = set()
    tmp = {}
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
                    rvsec_errors.append(to_error(right_term))
                case "RVSEC-COV":
                    cov = __cov_method_sig(right_term)
                    if cov.clazz not in called_methods:
                        called_methods[cov.clazz] = []
                        tmp[cov.clazz] = set()
                    if cov.unique_msg in tmp[cov.clazz]:
                        continue
                    tmp[cov.clazz].add(cov.unique_msg)
                    called_methods[cov.clazz].append(cov)
                    methods.append(cov)
    ordered_methods = sorted(methods, key=lambda x: x.time_occurred)
    return rvsec_errors, called_methods, ordered_methods


def __get_tag(line: str):
    tag = ""
    text = ""

    if ":" in line:
        idx = line.index(":")
        tag = line[2:idx].strip()
        text = line[idx + 1:].strip()

    return tag, text


def __cov_method_sig(text: str):
    sp = text.split(":::")

    clazz = sp[0].strip()
    method = sp[1].strip()
    params = sp[2].strip()

    return RvCoverageLog(clazz, method, params)
