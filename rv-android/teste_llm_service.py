import json
import logging
import os
import sys
from typing import Dict, Any

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType, ScreenParserType, VisitorType
from rvandroid.llm.frontier_models import FrontierModel
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.langchain_llm import LangchainLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.parser.static import static_analysis_parser


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def setup_preset_config(args, configurator):
    """Configura com base em presets pré-definidos"""
    preset = args.preset.lower() if args.preset else None

    if preset == "ollama":
        configurator.set_llm(
            llm_type=OllamaLLM.NAME,
            model=OllamaLLM.LLAMA,
            base_url="http://localhost:11434"
        )
        configurator.set_strategy("single_action")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "huggingface":
        configurator.set_llm(
            llm_type=HuggingFaceLLM.NAME,
            model=HuggingFaceLLM.LLAMA
        )
        configurator.set_strategy("single_action")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "dspy":
        configurator.set_llm(
            llm_type="dspy",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            provider="ollama"
        )
        configurator.set_strategy("dspy")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "langchain":
        configurator.set_llm(
            llm_type="langchain",
            model=LangchainLLM.LLAMA,
            base_url="http://localhost:11434",
            provider="ollama",
            use_json_parser=True,
            use_memory=False
        )
        configurator.set_strategy("single_action")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "claude":
        # Usando Claude com Anthropic API
        api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERRO: API key da Anthropic não fornecida. Defina --api-key ou a variável ANTHROPIC_API_KEY")
            sys.exit(1)

        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.CLAUDE_SONNET,
            provider="anthropic",
            api_key=api_key,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "openai":
        # Usando GPT com OpenAI API
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERRO: API key da OpenAI não fornecida. Defina --api-key ou a variável OPENAI_API_KEY")
            sys.exit(1)

        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.GPT_4,
            provider="openai",
            api_key=api_key,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "amazon":
        # Usando Claude no Amazon Bedrock
        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.NOVA_SONNET,
            provider="amazon",
            region=os.environ.get("AWS_REGION", "us-east-1"),
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    elif preset == "google":
        # Usando Gemini com Google API
        api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("ERRO: API key do Google não fornecida. Defina --api-key ou a variável GOOGLE_API_KEY")
            sys.exit(1)

        configurator.set_llm(
            llm_type="frontier",
            model=FrontierModel.GEMINI_PRO,
            provider="google",
            api_key=api_key,
            temperature=0.2
        )
        configurator.set_strategy("frontier")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

    else:
        # Se não tiver preset, configura com base nos argumentos diretos
        configurator.set_llm(
            llm_type=args.llm,
            model=args.model,
            base_url=args.base_url,
            provider=args.provider,
            api_key=args.api_key
        )
        configurator.set_strategy(args.strategy)
        configurator.set_parser(args.parser)
        configurator.set_visitor(args.visitor)


if __name__ == '__main__':
    # Configuração de logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "001"
    app_folder = screenshots_folder + "/" + apk
    droidbot_state_file = os.path.join(app_folder, f"{prefix}.state")
    srceenshot_file = os.path.join(app_folder, f"{prefix}.png")

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Inicializa o configurador
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.LLAMA,
        base_url="http://192.168.0.18:11434"
    )
    configurator.set_strategy(PromptStrategyType.STANDARD)
    configurator.set_parser(ScreenParserType.DROIDBOT)
    configurator.set_visitor(VisitorType.DEFAULT)

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
    service = LLMActionService(static_data, configurator)

    state = read_droidbot_state(droidbot_state_file)
    actions = service.process_state(state)
    print(f"Actions: {actions}")
