import logging
import sys

from rvandroid.parser.static import reach_parser
import logging
import os
import sys

from rvandroid.app import App
from rvandroid.parser.static import gator_parser, reach_parser, gesda_parser, static_analysis_parser
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
# from rvandroid.llm.prompt_generator import PromptGenerator
from rvandroid.llm.prompt_generator02 import PromptGenerator

import json

def read_json_to_dict(filename):
    with open(filename, 'r') as file:
        return json.load(file)

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
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"
    info_file = screenshot_folder+"/001.state"
    screen_info = read_json_to_dict(info_file)
    
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
    
    generator = PromptGenerator(classes, windows, wtg)
    
    text = generator.generate_prompt(screen_info)
    print(text)
    
