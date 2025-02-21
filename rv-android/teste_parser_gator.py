import logging
import os
import sys

from rvandroid.app import App
from rvandroid.parser.static import gator_parser, reach_parser, gesda_parser, static_analysis_parser
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows


def print_classes(classes: Classes):
    for clazz in classes.get_classes():
        print(f"Class: {clazz.name}")
        for method in clazz.methods:
            print(f"  Method: {method.name}")
            
def print_windows(windows: Windows):
    print("\nWindows:")
    for window in windows.windows:
        print(f"\nWindow: {window.name}")
        for w in window.widgets:
            widget = window.widgets[w]
            print(f"    - Widget ({widget.id}): {widget}")
            # for event in widget.events:
            #     print(f"        Event ({event.type.name}): {event.signature}")
                
def print_transitions(transitions):
    for transition in transitions.transitions:
        print(f"Transition: {transition.name}")
        print(f"  Source: {transition.source}")
        print(f"  Target: {transition.target}")
        print(f"  Event: {transition.event}")
        print(f"  Widget: {transition.widget}")
        print(f"  Widget Type: {transition.widget_type}")
        print(f"  Widget Listener: {transition.widget_listener}")
        print(f"  Widget Event Type: {transition.widget_event_type}")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")
    static_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static"
    apk = "cryptoapp.apk"    
    # apk = "byrne.utilities.hashpass_2.apk" 
    # apk = "ca.farrelltonsolar.classic_314.apk" 
    # apk = "com.example.openpass_1.apk" 
    # apk = "com.gianlu.dnshero_40.apk"
    
    windows = Windows()
    classes = Classes()
    app = App(os.path.join(static_folder, apk))
    package = app.package_name
        
    reach_file = os.path.join(static_folder, apk+".reach")
    classes = reach_parser.read_reachable_methods(reach_file)

    gator_file = os.path.join(static_folder, apk+".wtg")
    wtg = gator_parser.parse_gator_file(gator_file, package, classes, windows)
    
    gesda_file = os.path.join(static_folder, apk+".gesda")
    gesda_parser.parse_gesda_file(gesda_file, package, classes, windows)
    # print("fim gesda")

    classes, windows, wtg = static_analysis_parser.read_static_analysis_files(static_folder, apk, package)
    
    # exit(-1)

    # print_classes(classes)
    print_windows(windows)
    # print_transitions(wtg)  

    # print("\n\n...................................................")
    # for window in windows.windows:
    #     print(f"window={window}")
    #     for widget_id in window.widgets:
    #         widget = window.widgets[widget_id]
    #         print(f"\t-widget={widget}")
    #         for listener in widget.listeners:
    #             print(f"\t\t-listener={listener}")
                
    # print("\n\n...................................................")
    # print(f"wtg={wtg}")
