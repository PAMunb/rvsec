import logging
import os
import sys

from rvandroid.app import App
from rvandroid.parser.static import static_analysis_parser
# from rvandroid.llm.prompt_strategy_basic import BasicPromptStrategy001
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
import json

def read_json_to_dict(filename):
    with open(filename, 'r') as file:
        return json.load(file)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    
    logging.info("Starting...")
    # static_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static"
    apk = "cryptoapp.apk"    
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/"+apk
    info_file = screenshot_folder+"/001.state"
    
    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name
    
    screen_info = read_json_to_dict(info_file)
        
    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

    # strategy_type = "basic"
    # prompt_strategy = PromptStrategyFactory.create(strategy_type, static_data)
    # prompt_strategy = BasicPromptStrategy001(static_data)
    prompt_strategy = SingleActionPromptStrategy(static_data)

    system_prompt = prompt_strategy.generate_system_prompt()
    user_prompt = prompt_strategy.generate_user_prompt(screen_info)

    print(f"System prompt:\n{system_prompt}")
    print(f"\n\nUser prompt:\n{user_prompt}")
    
