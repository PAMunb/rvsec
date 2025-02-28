import os

from rvandroid.llm.model_factory import ModelFactory
from rvandroid.llm.prompt_strategy_factory import PromptStrategyFactory
from rvandroid.parser.parser_factory import ParserFactory, ParserType
from rvandroid.model.static import StaticAnalysisData

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


# Criar componentes individuais
def custom_testing_pipeline(state_data, static_data):
    # 1. Criar parser
    parser = ParserFactory.create(ParserType.DROIDBOT)
    print(f"Parser: {parser.parse(state_data, static_data)}")

    # 2. Criar estratégia de prompt
    prompt_strategy = PromptStrategyFactory.create(
        "basic",
        static_data,
        ParserType.DROIDBOT
    )

    # 3. Criar modelo de linguagem
    llm = ModelFactory.create(
        "huggingface",
        "Qwen/Qwen2.5-3B-Instruct"
    )

    # 4. Gerar prompts
    messages = prompt_strategy.generate_prompts(state_data)

    # 5. Gerar resposta
    response = llm.generate(messages)

    # 6. Processar resposta (simplificado)
    import json
    import re

    # Extrair JSON da resposta
    json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            actions = json.loads(json_str)
            return actions
        except json.JSONDecodeError:
            return []

    # 7. Limpar recursos
    llm.clean()

    return []


def read_state_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)


# Uso
apk = "cryptoapp.apk"
screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/" + apk
info_file = screenshot_folder + "/009.state"
app = App(os.path.join(screenshot_folder, apk))
package = app.package_name

# Load static analysis data
static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)
droidbot_data = read_state_file(info_file)

actions = custom_testing_pipeline(droidbot_data, static_data)
print(f"Ações recomendadas: {actions}")
