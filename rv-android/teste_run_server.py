# teste_run_server.py
import json
import logging
import os
import sys
import time
import argparse

from rvandroid.app import App
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.frontier_models import FrontierModel
from rvandroid.llm.langchain_llm import LangchainLLM
from rvandroid.server import Server
from rvandroid.parser.static import static_analysis_parser
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.service.action_service import LLMActionService


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='RV-Android Server')

    # LLM e modelo
    parser.add_argument('--llm', choices=['ollama', 'huggingface', 'dspy', 'langchain', 'frontier'],
                        default='ollama', help='Tipo de LLM')
    parser.add_argument('--model', help='Nome do modelo')

    # URL do Ollama e outros parâmetros
    parser.add_argument('--base-url', default='http://localhost:11434',
                        help='URL base para o servidor Ollama')

    # Estratégia, Parser e Visitor
    parser.add_argument('--strategy', choices=['basic', 'dspy', 'single_action', 'frontier'],
                        default='single_action', help='Estratégia de prompt')
    parser.add_argument('--parser', choices=['droidbot', 'uiautomator'],
                        default='droidbot', help='Parser de tela')
    parser.add_argument('--visitor', choices=['enhanced'],
                        default='enhanced', help='Visitor para elementos da UI')

    # Parâmetros adicionais
    parser.add_argument('--provider', help='Provider para frontier models ou langchain/dspy')
    parser.add_argument('--api-key', help='API key para serviços remotos')
    parser.add_argument('--preset',
                        choices=['ollama', 'huggingface', 'dspy', 'langchain', 'claude', 'openai', 'amazon', 'google'],
                        help='Preset de configuração para facilitar uso')

    args = parser.parse_args()
    return args


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

    # Parse argumentos
    args = parse_arguments()

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = screenshots_folder + "/" + apk

    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    # Inicializa o configurador
    configurator = ComponentConfigurator(static_data)

    # Se tiver um preset definido, usa ele, senão configura manualmente
    if args.preset:
        setup_preset_config(args, configurator)
    else:
        # Exemplos de configurações pré-definidas. Descomente apenas uma por vez!

        # DSPY
        # configurator.set_llm(
        #     llm_type="dspy",
        #     model="llama3.2:3b",
        #     base_url="http://localhost:11434",
        #     provider="ollama"
        # )
        # # configurator.set_strategy("dspy")
        # configurator.set_strategy("dspy_single_action")
        # configurator.set_parser("droidbot")
        # configurator.set_visitor("enhanced")

        # # OLLAMA
        configurator.set_llm(
            llm_type=OllamaLLM.NAME,
            model=OllamaLLM.GEMMA,
            base_url="http://localhost:11434"
        )
        configurator.set_strategy("single_action")
        configurator.set_parser("droidbot")
        configurator.set_visitor("enhanced")

        # # HUGGING FACE
        # configurator.set_llm(
        #     llm_type=HuggingFaceLLM.NAME,
        #     model=HuggingFaceLLM.GEMMA
        # )
        # configurator.set_strategy("single_action")
        # configurator.set_parser("droidbot")
        # configurator.set_visitor("enhanced")

        # # LANGCHAIN
        # configurator.set_llm(
        #     llm_type="langchain",
        #     model=LangchainLLM.LLAMA,
        #     base_url="http://localhost:11434",
        #     provider="ollama"
        # )
        # configurator.set_strategy("single_action")
        # configurator.set_parser("droidbot")
        # configurator.set_visitor("enhanced")

        # # CLAUDE (ANTHROPIC)
        # api_key = os.environ.get("ANTHROPIC_API_KEY")
        # configurator.set_llm(
        #     llm_type="frontier",
        #     model=FrontierModel.CLAUDE_SONNET,
        #     provider="anthropic",
        #     api_key=api_key
        # )
        # configurator.set_strategy("frontier")
        # configurator.set_parser("droidbot")
        # configurator.set_visitor("enhanced")

        # Configuração padrão se nenhuma for selecionada
        # configurator.set_llm(
        #     llm_type=args.llm,
        #     model=args.model or OllamaLLM.LLAMA,
        #     base_url=args.base_url,
        #     provider=args.provider,
        #     api_key=args.api_key
        # )
        # configurator.set_strategy(args.strategy)
        # configurator.set_parser(args.parser)
        # configurator.set_visitor(args.visitor)

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
    # service = configurator.create_service()
    service = LLMActionService(static_data, configurator)

    # Inicia o servidor
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

# Exemplos de uso com diferentes configurações:

# # Usar Ollama com modelo llama3.2:3b (padrão)
# python teste_run_server.py
#
# # Usar DSPy com modelo phi3.5:3.8b e estratégia DSPy
# python teste_run_server.py --llm dspy --model phi3.5:3.8b --strategy dspy
#
# # Usar Hugging Face com modelo Phi-3.5
# python teste_run_server.py --llm huggingface --model microsoft/Phi-3.5-mini-instruct
#
# # Usar LangChain com Ollama como provedor
# python teste_run_server.py --llm langchain --provider ollama --model llama3.2:3b
#
# # Usar Claude (modelo frontier)
# python teste_run_server.py --llm frontier --model claude-3-5-sonnet-20241022 --provider anthropic --api-key sk-ant-... --strategy frontier
#
# # Usar GPT-4 (modelo frontier)
# python teste_run_server.py --llm frontier --model gpt-4-turbo-2024-04-09 --provider openai --api-key sk-... --strategy frontier
#
# # Usar presets para configuração mais fácil
# python teste_run_server.py --preset ollama
# python teste_run_server.py --preset huggingface
# python teste_run_server.py --preset dspy
# python teste_run_server.py --preset langchain
# python teste_run_server.py --preset claude --api-key sk-ant-...
# python teste_run_server.py --preset openai --api-key sk-...