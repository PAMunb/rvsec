import logging
import sys

from rvandroid.domain.window import Windows
from rvandroid.parser.static import reach_parser, gesda_parser
from rvandroid.parser.static.gesda_parser import GesdaParser
from rvandroid.parser.static.reach_parser import ReachParser
from rvandroid.util.logging.manager import LoggingManager

if __name__ == '__main__':

    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=True,
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        console_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    windows = Windows()

    reach_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.reach"
    reach_parser = ReachParser()
    classes = reach_parser.parse_file(reach_file, None, None, None)

    gesda_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.gesda"
    # gesda_parser = GesdaParser()
    # gesda_parser.parse_file(gesda_file, "", classes, windows)
    gesda_parser.parse_gesda_file(gesda_file, "", classes, windows)

    if windows is None:
        print("Error parsing GESDA file")
        exit(-1)
    for window in windows.windows:
        print(f"window={window}")
        for widget_id in window.widgets:
            widget = window.widgets[widget_id]
            print(f"\t-widget={widget}")
            for event in widget.events:
                print(f"\t\t-event={event}")
