import logging
import sys

from rvandroid.parser import gesda_parser, reach_parser, gator_parser

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    reach_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static//cryptoapp.apk.reach"
    classes = reach_parser.read_reachable_methods(reach_file)

    gesda_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.gesda"
    windows = gesda_parser.parse_gesda_file(gesda_file, classes)

    gator_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.wtg"
    gator_parser.parse_gator_file(gator_file, classes, windows)
    exit(-1)

    for w in windows:
        window = windows[w]
        print(f"window={window}")
        for widget in window.widgets:
            print(f"\t-widget={widget}")
            for listener in widget.listeners:
                print(f"\t\t-listener={listener}")
