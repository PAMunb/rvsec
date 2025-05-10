import json
import logging
import os
import sys
from typing import Dict, Any

import torch
from transformers import AutoProcessor, Gemma3ForConditionalGeneration
from transformers import BitsAndBytesConfig

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType, VisitorType, StateEntry
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.static import static_analysis_parser


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    with open(filename, 'r') as file:
        return json.load(file)


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData):
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    screen_description: ScreenDescription = parser.parse(screen_info, static_data)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info[StateEntry.VIEW_TREE],
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }
    return state


def create_ollama_config(model_name: str, static_data: StaticAnalysisData,
                         strategy=PromptStrategyType.BATCH_ACTION,
                         visitor=VisitorType.DEFAULT,
                         temperature=0.2, max_tokens=1200):
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=model_name,
        base_url="http://127.0.0.1:11434",
        temperature=temperature,
        max_tokens=max_tokens
    )
    configurator.set_strategy(strategy)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(visitor)
    return configurator


def create_huggingface_config(model_name: str, static_data: StaticAnalysisData,
                              strategy=PromptStrategyType.BATCH_ACTION,
                              visitor=VisitorType.DEFAULT,
                              temperature=0.2, max_tokens=1000):
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=HuggingFaceLLM.NAME,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens
    )
    configurator.set_strategy(strategy)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(visitor)
    return configurator


def tmp_001(service, state):
    actions = service.process_state(state)
    print(f"\nActions: {len(actions)}")
    for action in actions:
        print(f"   - {action}")
        for key in action.keys():
            print(f"      {key}: {action[key]}")


def tmp_002(service, state):
    while True:
        input("Press Enter to continue...")
        tmp_001(service, state)


def tmp_gemma():
    model_id = "google/gemma-3-4b-it"
    torch_dtype = torch.bfloat16

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch_dtype,
        bnb_4bit_quant_type="nf4"
    )
    print(f"quantization_config={quantization_config}")

    model = Gemma3ForConditionalGeneration.from_pretrained(
        model_id, device_map="auto", quantization_config=quantization_config
    ).eval()

    processor = AutoProcessor.from_pretrained(model_id)

    # pipe = pipeline(
    #     "image-text-to-text",
    #     model="google/gemma-3-4b-it",
    #     device="cuda",
    #     torch_dtype=torch.bfloat16
    # )

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}]
        },
        {
            "role": "user",
            "content": [
                {"type": "image",
                 "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/p-blog/candy.JPG"},
                {"type": "text", "text": "What animal is on the candy?"}
            ]
        }
    ]
    print(f"messages={messages}")

    # output = pipe(text=messages, max_new_tokens=200)
    # print(output[0]["generated_text"][-1]["content"])

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device, dtype=torch.bfloat16)
    print(f"inputs={inputs}")

    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generation = model.generate(**inputs, max_new_tokens=200, do_sample=True)
        print(f"generation={generation}")
        generation = generation[0][input_len:]
        print(f"generation={generation}")

    decoded = processor.decode(generation, skip_special_tokens=True)
    print("RESPOSTA:")
    print(decoded)

    import gc
    del model, inputs
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == '__main__':
    # Configuração de logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)

    # tmp_gemma()
    # exit(1)

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "009"
    app_folder = screenshots_folder + "/" + apk
    droidbot_state_file = os.path.join(app_folder, f"{prefix}.state")
    srceenshot_file = os.path.join(app_folder, f"{prefix}.png")

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    state = create_state_from_droidbot_state(droidbot_state_file, srceenshot_file, package, static_data)

    # Inicializa o configurador
    # configurator = create_ollama_config(OllamaLLM.DEEPSEEK, static_data)
    # configurator = create_ollama_config(OllamaLLM.LLAMA, static_data)
    configurator = create_huggingface_config(HuggingFaceLLM.DEEPSEEK, static_data)

    # Mostra a configuração
    config = configurator.describe_configuration()
    print("\n=== Configuração do RV-Android ===")
    print(f"LLM: {config['llm']['type']}")
    print(f"Modelo: {config['llm']['model']}")
    print(f"Estratégia: {config['strategy']}")
    print(f"Parser: {config['parser']}")
    print(f"Visitor: {config['visitor']}")
    print("================================\n")

    # Cria o serviço
    service = LLMActionService(static_data, configurator, package)

    tmp_001(service, state)
    # tmp_002(service, state)

    service.llm_manager.cleanup()

    # print(f"state_processing_total={PerformanceMonitor.get_instance().get_metrics_by_name("state_processing_total")}")
    # print(f"response_total_duration={PerformanceMonitor.get_instance().get_metrics_by_name("response_total_duration")}")
    # print(f"response_load_duration={PerformanceMonitor.get_instance().get_metrics_by_name("response_load_duration")}")
    # print(f"response_total_duration={PerformanceMonitor.get_instance().get_metrics_stats("response_total_duration")}")
