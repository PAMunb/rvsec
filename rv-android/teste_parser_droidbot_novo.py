# Example usage
import logging
import os
import sys
import json

from rvandroid.app import App
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.parser_factory import ParserFactory, ParserType
from rvandroid.parser.static import static_analysis_parser
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
def read_state_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("datasets").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("androguard").setLevel(logging.ERROR)

# Load app information
apk = "cryptoapp.apk"
screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/"+apk
info_file = screenshot_folder+"/009.state"
app = App(os.path.join(screenshot_folder, apk))
package = app.package_name

# Load static analysis data
static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

# Parse DroidBot state
droidbot_data = read_state_file(info_file)
droidbot_parser = ParserFactory.create(ParserType.DROIDBOT)
droidbot_screen_description = droidbot_parser.parse(droidbot_data, static_data)
print(f"DroidBot screen description:\n{droidbot_screen_description}")

# Parse UIAutomator2 state
# uiautomator_data = read_state_file("/path/to/uiautomator_state.json")
# uiautomator_parser = ParserFactory.create(ParserType.UIAUTOMATOR)
# uiautomator_screen_description = uiautomator_parser.parse(uiautomator_data, static_data)
# print(f"UIAutomator2 screen description:\n{uiautomator_screen_description}")

# Using with LLMActionService
from rvandroid.service.llm_action_service import LLMActionService

# Create service with DroidBot parser
droidbot_service = LLMActionService(
    static_data=static_data,
    model_type="huggingface",
    model_name=HuggingFaceLLM.QWEN,
    strategy_type="basic",
    parser_type=ParserType.DROIDBOT
)

# Process state and get actions
droidbot_actions = droidbot_service.process_state(droidbot_data)
print(f"DroidBot suggested actions: {droidbot_actions}")

# # Create service with UIAutomator2 parser
# uiautomator_service = LLMActionService(
#     static_data=static_data,
#     model_type="ollama",
#     model_name="llama3.2:3b",
#     strategy_type="basic",
#     parser_type=ParserType.UIAUTOMATOR
# )
#
# # Process state and get actions
# uiautomator_actions = uiautomator_service.process_state(uiautomator_data)
# print(f"UIAutomator2 suggested actions: {uiautomator_actions}")