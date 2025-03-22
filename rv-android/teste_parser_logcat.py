import logging
import os
import sys

import rvandroid.parser.log.logcat_parser as parser
from rvandroid.analysis.coverage_tracker import CoverageTracker
from rvandroid.app import App
from rvandroid.model.coverage import LogcatRepository, CoverageMetrics
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.static import static_analysis_parser


def tmp_001(logcat_file: str):
    repository: LogcatRepository = parser.parse_logcat_file(logcat_file)
    print(f"repository={repository}")
    metrics: CoverageMetrics = repository.calculate_metrics()
    print(f"metrics={metrics}")


def tmp_002(logcat_file: str, data: StaticAnalysisData):
    tracker = CoverageTracker(logcat_file, data)
    tracker.start()
    print("INICIOU ............")
    # time.sleep(5)
    print(tracker.get_coverage_metrics())
    print("parando")
    tracker.stop()
    print(tracker.get_coverage_metrics())


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    log_file = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/experiment_20250321123409/cryptoapp.apk/cryptoapp.apk__1__60__ape.logcat"

    apk = "cryptoapp.apk"
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/" + apk
    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name
    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

    # tmp_001(log_file)

    tmp_002(log_file, static_data)
