import json
import logging
import os
import sys
import time
from rvandroid.config.component_config import ComponentConfig
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.parser.screen.visitor import EnhancedTextVisitor
from rvandroid.app import App
from rvandroid.parser.static import static_analysis_parser
from rvandroid.service.llm_action_service import LLMActionService
from rvandroid.server import Server

def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)
    
    
if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")
    
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = screenshots_folder+"/"+apk

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    config = ComponentConfig()
    config.set_strategy(BasicPromptStrategy001)
    config.set_visitor(EnhancedTextVisitor)

    service = LLMActionService(static_data, component_config=config)
    
    server = Server(service)
    try:
        if server.start():
            print("Server started successfully")
            while True:
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.stop()   
    
    print("Server started")
