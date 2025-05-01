#!/usr/bin/env python3

"""
RV-Android Prompt Framework Test.

Este arquivo contém exemplos simplificados de como usar o framework de prompts
refatorado do RV-Android.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.constants import PromptStrategyType, StateEntry
from rvandroid.llm.constants import ScreenParserType, VisitorType
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid.llm.prompt.information.fragments.screenshot_fragment import ScreenshotFragment
from rvandroid.llm.prompt.information.fragments.ui_elements_fragment import UIElementsFragment
from rvandroid.llm.prompt.information.fragments.ui_pattern_fragment import UIPatternFragment
from rvandroid.llm.prompt.template.xml_repository import XMLTemplateRepository
from rvandroid.llm.service import StateEnricher
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.parser.static import static_analysis_parser
from rvandroid.util.logging.manager import LoggingManager


# Helper functions for loading data

def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def enrich_state(state, static_data: StaticAnalysisData, config: ComponentConfigurator):
    enricher = StateEnricher(static_data, config)
    return enricher.enrich_state(state)


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData):
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    screen_description: ScreenDescription = parser.parse(screen_info, static_data)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info[StateEntry.VIEW_TREE],
        StateEntry.STRUCTURED_SCREEN: screen_description,
        StateEntry.SCREENSHOT_PATH: screenshot_path
    }
    return state


def tmp_001(droidbot_state_file, screenshot_path, package, static_data):
    state = create_state_from_droidbot_state(droidbot_state_file, screenshot_path, package, static_data)

    # Inicializa o configurador
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.QWEN,
        base_url="http://localhost:11434"
    )
    configurator.set_strategy(PromptStrategyType.BATCH_ACTION)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(VisitorFactory.DEFAULT)

    prompt_framework = PromptFramework.create(configurator)

    state = enrich_state(state, static_data, configurator)
    show_state(state)


def show_state(state):
    print("State:")
    for key, value in state.items():
        print(f"{key}: {value}")


def tmp_002(droidbot_state_file, screenshot_path, package, static_data):
    state = create_state_from_droidbot_state(droidbot_state_file, screenshot_path, package, static_data)

    # Inicializa o configurador
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.QWEN,
        base_url="http://localhost:11434"
    )
    configurator.set_strategy(PromptStrategyType.BATCH_ACTION)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(VisitorFactory.DEFAULT)

    prompt_framework = PromptFramework.create(configurator)

    state = enrich_state(state, static_data, configurator)

    prompt = prompt_framework.generate_mcp_prompt(state)
    # print(prompt)

    for msg in prompt:
        for content in msg.content:
            print(content.text)


if __name__ == "__main__":
    # Configure logging with DEBUG level to see more details
    LoggingManager.get_instance().configure_output(console_level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.classes.Classes").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Windows").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.widget.Widget").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.reach").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.gator").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.static.gesda").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.util.utils").setLevel(logging.WARNING)

    # Define paths to files
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "009"
    app_folder = os.path.join(screenshots_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")
    screenshot_path = os.path.join(app_folder, prefix + ".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")
    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    static_data = static_analysis_parser.parse(reach_file, gator_file, gesda_file, package)

    # Check if files exist
    if not os.path.exists(droidbot_state_file):
        print(f"State file not found: {droidbot_state_file}")
        sys.exit(1)

    # Run examples
    tmp_001(droidbot_state_file, screenshot_path, package, static_data)
