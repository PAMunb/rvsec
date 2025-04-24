import logging
import sys

from rvandroid.app import App
from rvandroid.parser.static.static_analysis_parser import StaticAnalysisParser
from settings import *


def runXXX():
    static_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static"
    apk = "cryptoapp.apk"
    app = App(os.path.join(static_folder, apk))
    package = app.package_name
    reach_file = os.path.join(static_folder, apk + ".reach")
    gator_file = os.path.join(static_folder, apk + ".wtg")
    gesda_file = os.path.join(static_folder, apk + ".gesda")

    parser = StaticAnalysisParser()
    static_data = parser.parse(reach_file, gator_file, gesda_file, package)

    print(static_data)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.ERROR)

    runXXX()

    print("FIM DE FESTA!!!")
