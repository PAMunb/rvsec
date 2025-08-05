#!/usr/bin/env python3
"""
Manual test for prompt generation with template architecture.

This test validates that the prompt generation system works correctly with:
- Templates in rvandroid-tool
- RvAndroidToolConfig for parser/visitor configuration
- Template registration with PromptFramework
- Clean LLMConfig integration
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

from rv_llm import LLMMessage, LLMRole, LLMTextContent, LLMImageContent
from rv_llm.config import PromptConfig
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.prompt import RVAndroidPromptFramework

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))

# Import constants after path setup
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_llm.llm.constants import StateEntry
from rv_android_core import constants
from rv_android_core.domain.app import App
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rv_llm.llm.prompt.framework import PromptFramework
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_android_core.domain.static import StaticAnalysisData
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.transition_manager import TransitionManager
from rvandroid_tool.llm.service.action_service import LLMActionService

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)
os.environ[constants.ENV_RVSEC_HOME] = parent_directory


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    from rv_android_core.util.logging.manager import LoggingManager

    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,
        file_level=10,
        json_format=False
    )

    return logging_manager.get_logger('teste.prompt_generator')


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def enrich_state(state, static_data: StaticAnalysisData, config: RvAndroidToolConfig):
    memory_manager = MemoryManager(static_data=static_data)
    transition_manager = TransitionManager(static_data=static_data)
    llm_service = LLMActionService(
        static_data=static_data,
        tool_config=config
    )

    # Override service's managers with our instances for testing
    llm_service.memory_manager = memory_manager
    llm_service.transition_manager = transition_manager

    llm_service._pre_process_state(state)
    return state


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData):
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ScreenParserType.DROIDBOT, BasicTextVisitor)
    screen_description: ScreenDescription = parser.parse_screen(screen_info, static_data)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info[StateEntry.VIEW_TREE],
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }
    return state


def tmp_001(droidbot_state_file, screenshot_path, package, static_data):
    setup_logging()

    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.QWEN,
        temperature=0.3,
        max_tokens=800
    )
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        max_context_length=8192
    )
    tool_config = RvAndroidToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config
    )

    framework = RVAndroidPromptFramework.create(prompt_config)

    basic_state = create_state_from_droidbot_state(droidbot_state_file, screenshot_path, package, static_data)
    state = enrich_state(basic_state, static_data, tool_config)

    prompt = framework.generate_prompt(state)
    print(f"\nprompt={prompt}")

    for msg in prompt:
        print(f"\n\n*************** ROLE: {msg.role} ::: contents={len(msg.content)}")
        for content in msg.content:
            print(content)

    return prompt

def save_prompt(prompt: list[LLMMessage], out_dir, prefix):
    for message in prompt:
        text = ""
        image = ""
        for content in message.content:
            if isinstance(content, LLMTextContent):
                text += content.text
            elif isinstance(content, LLMImageContent):
                image += content.encoded_string

        if LLMRole.USER == message.role:
            suffix = "_user.txt"
        else: # LLMRole.SYSTEM == message.role:
            suffix = "_system.txt"

        with open(os.path.join(out_dir, prefix + suffix)  , "w") as file:
            file.write(text)

        if image:
            with open(os.path.join(out_dir, prefix + "_image.txt")  , "w") as file:
                file.write(image)


if __name__ == '__main__':
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "015"  # 001, 009, 015
    app_folder = os.path.join(screenshots_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")
    screenshot_path = os.path.join(app_folder, prefix + ".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")
    app = App(app_path=os.path.join(app_folder, apk))
    package = app.package_name

    static_analysis_parser = StaticAnalysisParser()

    static_data = static_analysis_parser.parse(reach_file, gator_file, gesda_file, package)

    prompt = tmp_001(droidbot_state_file, screenshot_path, package, static_data)

    outdir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-evaluator/src/rv_evaluator/prompts"
    save_prompt(prompt, outdir, prefix)

    # print("=== Testing Template System ===")
    # tmp_template_system()
