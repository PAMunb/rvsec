#!/usr/bin/env python3

import base64
from ollama import ChatResponse, Client
import requests
import os
import base64

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

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
from rv_llm.llm.constants import StateEntry, PromptStrategyType
from rv_android_core import constants
from rv_android_core.domain.app import App
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_llm.config.llm_config import LLMConfig
from rv_llm.config.prompt_config import PromptConfig
from rv_llm.llm.constants import LLMType
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_android_core.domain.static import StaticAnalysisData
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.transition_manager import TransitionManager
from rvandroid_tool.llm.service.action_service import LLMActionService

# Import refactored framework
from rvandroid_tool.llm.prompt.rvandroid_framework import RVAndroidPromptFramework
from rv_llm.factories.component_factory import LLMComponentFactory

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

    return logging_manager.get_logger('teste.prompt_generator_refactored')


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def enrich_state(state, static_data: StaticAnalysisData, config: RvAndroidToolConfig):
    memory_manager = MemoryManager(static_data=static_data)
    transition_manager = TransitionManager(static_data)
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

def get_image_base64_local(image_path: str) -> str:
    """
    Lê uma imagem de um arquivo local e retorna sua string codificada em base64.
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except FileNotFoundError:
        print(f"Erro: O arquivo de imagem não foi encontrado em: {image_path}")
        return None
    except Exception as e:
        print(f"Erro ao ler ou codificar a imagem local: {e}")
        return None

def get_image_base64(image_url: str) -> str:
    """Fetches an image from a URL and returns its base64 encoded string."""
    response = requests.get(image_url)
    response.raise_for_status()  # Raise an exception for bad status codes
    return base64.b64encode(response.content).decode('utf-8')


def tmp_001():
    model_name = "gemma3:4b" # Make sure this model is multimodal capable, e.g., llava or llama3.2-vision
    image_url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg"

    # Get the base64 encoded image
    try:
        image_base64 = get_image_base64(image_url)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        return

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Describe this image in detail.", # Content is a string
            "images": [image_base64]                     # Images array within the message
        }
    ]
    client = Client(host="http://localhost:11434")
    options = {
        "temperature": 0.2,
        "num_predict": 100,
        "top_p": 0.5,
        "top_k": 10
    }

    print(f"Attempting to chat with model: {model_name}")
    try:
        response: ChatResponse = client.chat(
            model=model_name,
            messages=messages,
            options=options,
            stream=False,
            keep_alive="30s"
        )

        print(f"\n<<< response=\n{response}")
        print(f"response.total_duration={response.total_duration}")
    except Exception as e:
        print(f"An error occurred during the chat request: {e}")


def tmp_002(screenshot_file):
    model_name = "gemma3:4b" #"llama3.2-vision:11b" #"granite3.2-vision:2b" #"qwen2.5vl:3b" #"gemma3:4b"

    try:
        image_base64 = get_image_base64_local(screenshot_file)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        return

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Describe this android app screenshot in detail. informing all the fields that you find. verify error indicators too",
            "images": [image_base64]
        }
    ]
    client = Client(host="http://localhost:11434")
    options = {
        "temperature": 0.2,
        "num_predict": 800,
        "top_p": 0.5,
        "top_k": 10
    }

    print(f"Attempting to chat with model: {model_name}")
    try:
        response: ChatResponse = client.chat(
            model=model_name,
            messages=messages,
            options=options,
            stream=False,
            keep_alive="30s"
        )

        print(f"\n<<< response=\n{response}")
        print(f"\n<<< {response.message.content}")
        print(f"response.total_duration={response.total_duration}")
    except Exception as e:
        print(f"An error occurred during the chat request: {e}")

def tmp_003(droidbot_state_file, screenshot_path, package, static_data):
    print("tmp_003")
    # Create configurations
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,
        vision=True,
        think=False,
        temperature=0.2,
        max_tokens=1000
    )
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        max_context_length=8192
    )
    tool_config = RvAndroidToolConfig(
        prompt_config=prompt_config,
        llm_config=llm_config
    )
    framework = RVAndroidPromptFramework.create(prompt_config)

    basic_state = create_state_from_droidbot_state(droidbot_state_file, screenshot_path, package, static_data)
    state = enrich_state(basic_state, static_data, tool_config)

    # llm = OllamaLLM(config=llm_config)
    llm = LLMComponentFactory.create_llm(llm_config)

    messages = framework.generate_prompt(state)

    # print(f"\n<<< messages=\n{messages}")
    # for msg in messages:
    #     print(f"{msg.role}: {len(msg.content)}")
    #     for content in msg.content:
    #         print(f"CONTENT - {type(content)}={content}")
    # exit(1)

    import time
    start_time = time.time()
    times = []
    for _ in range(10):
        start = time.time()

        response = llm.generate(messages)

        end = time.time()
        times.append(end - start)

        print(f"\n<<< response=\n{response}")
        print(f"**************** response.total_duration={response.total_duration}")

    total_time = time.time() - start_time
    print(f"\n#############################\nTotal time: {total_time}")
    print(f"Average time: {sum(times) / len(times)}")




if __name__ == '__main__':
    setup_logging()

    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "001"  # 001, 009, 015
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

    # tmp_001()
    tmp_002(screenshot_path)
    # tmp_003(droidbot_state_file, screenshot_path, apk, static_data)