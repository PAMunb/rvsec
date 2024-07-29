import os
from csv import DictReader, DictWriter

from androguard.core.analysis.analysis import Analysis, MethodAnalysis, ClassAnalysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK

# incluir colunas:
# - experiment: se o apk faz arte do experimento
# - instrumented: se o apk foi instrumentado
# - jca_error: se foi encontrado erro no apk ou nao
if __name__ == '__main__':
    csv_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/fdroid/final_apps_to_download.csv"
    results_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/merged_results_analysis.json"
    instrument_errors_file = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/merged_instrument_errors.json"
    apks_path = "/pedro/desenvolvimento/RV_ANDROID/apks"

    # tmp_verifica_package(apks_path)
    # execute(apks_path, csv_file)
