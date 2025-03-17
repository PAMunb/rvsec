import logging
import os
import sys

import rvandroid.parser.log.logcat_parser as parser
from rvandroid.analysis.coverage_tracker import CoverageTracker
from rvandroid.app import App
from rvandroid.parser.static import static_analysis_parser


def tmp_001(log_file: str):
    rvsec_errors, called_methods, sorted_methods = parser.parse_logcat_file(log_file)

    print("ERROS: {}".format(len(rvsec_errors)))
    for erro in rvsec_errors:
        print(erro)

    print("\n\nMETODOS ...........")
    for clazz in called_methods:
        print(clazz)
        for metodo in called_methods[clazz]["methods"]:
            m = called_methods[clazz]["methods"][metodo]
            print("   - {} ::: {}".format(metodo, m))


def tmp_002(log_file: str, static_data):
    tracker = CoverageTracker(log_file, static_data)
    tracker.start()
    # time.sleep(5)
    print(tracker.get_coverage_metrics())
    print("parando")
    tracker.stop()
    print(tracker.get_coverage_metrics())


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    log_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/experiment_20250317095105/cryptoapp.apk/cryptoapp.apk__1__60__ape.logcat"

    apk = "cryptoapp.apk"
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/" + apk
    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name
    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

    # tmp_001(log_file)

    tmp_002(log_file, static_data)
