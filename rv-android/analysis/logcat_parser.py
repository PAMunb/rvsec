
def parse_logcat_file(log_file: str):
    called_methods = {}
    rvsec_errors = set()
    with open(log_file) as f:
        while True:
            line = f.readline()
            if not line:
                break
            tag, right_term = __get_tag(line)
            match tag:
                case "RVSEC":
                    print("RVSEC={}".format(right_term))
                    rvsec_errors.add(right_term)
                case "RVSEC-COV":
                    clazz, method, params = __cov_method_sig(right_term)
                    sig = method + params

                    if clazz not in called_methods:
                        called_methods[clazz] = set()
                    called_methods[clazz].add(sig)

    return rvsec_errors, called_methods


def __get_tag(line: str):
    tag = ""
    text = ""

    if ":" in line:
        idx = line.index(":")
        tag = line[2:idx].strip()
        text = line[idx+1:].strip()

    return tag, text


def __cov_method_sig(text: str):
    tmp01 = text.split("(")
    tmp = tmp01[0].split(" ")[-1]

    clazz = tmp[:tmp.rindex(".")].strip()
    method = tmp[tmp.rindex(".") + 1:].strip()
    params = "(" + tmp01[1]

    return clazz, method, params.replace(", ", ",")
