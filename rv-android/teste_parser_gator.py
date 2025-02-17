import logging
import sys

from rvandroid.parser import gesda_parser, reach_parser, gator_parser
from rvandroid.parser.classes import Windows

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")
    apk = "cryptoapp.apk"
    package = "br.unb.cic.cryptoapp"
    windows = Windows()
    
    reach_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.reach"
    classes = reach_parser.read_reachable_methods(reach_file)

    gesda_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.gesda"
    gesda_parser.parse_gesda_file(gesda_file, package, classes, windows)
    print("fim gesda")

    gator_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.wtg"
    wtg = gator_parser.parse_gator_file(gator_file, package, classes, windows)
    # exit(-1)

    print("\n\n...................................................")
    for w in windows.windows:
        window = windows.windows[w]
        print(f"window={window}")
        for widget_id in window.widgets:
            widget = window.widgets[widget_id]
            print(f"\t-widget={widget}")
            for listener in widget.listeners:
                print(f"\t\t-listener={listener}")
                
    print("\n\n...................................................")
    print(f"wtg={wtg}")
