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

    print("XXX")
    for c in called_methods:
        print(c)
        for m in called_methods[c]:
            print("   - {}".format(m))
    print("*********************")
    print("RVSEC:")
    for e in rvsec_errors:
        print(">> {}".format(e))

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
    # the params
    tmp01 = text.split("(")
    # modifiers and return
    tmp = tmp01[0].split(" ")[-1]

    clazz = tmp[:tmp.rindex(".")].strip()
    method = tmp[tmp.rindex(".") + 1:].strip()
    params = "(" + tmp01[1]

    return clazz, method, params


if __name__ == '__main__':
    log = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/teste.logcat"
    parse_logcat_file(log)
