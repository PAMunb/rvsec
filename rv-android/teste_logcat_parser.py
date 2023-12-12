from analysis import logcat_parser


if __name__ == '__main__':
    log = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/20231212113846/com.example.openpass_1.apk/com.example.openpass_1.apk__1__120__monkey.logcat"

    rvsec_errors, called_methods = logcat_parser.parse_logcat_file(log)

    for clazz in called_methods:
        print(clazz)
        for m in called_methods[clazz]:
            print("   - {}".format(m))
