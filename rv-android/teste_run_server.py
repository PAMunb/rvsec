# teste_run_server.py
import json
import logging
import os
import sys
import time
import argparse

from rvandroid.app import App
from rvandroid.server import Server
from rvandroid.parser.static import static_analysis_parser
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.huggingface_llm import HuggingFaceLLM

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
    parser.add_argument('--strategy', choices=['basic', 'dspy', 'single_action'],
                        default='basic', help='Estratégia de prompt')
    parser.add_argument('--parser', choices=['droidbot', 'uiautomator'],
                        default='droidbot', help='Parser de tela')
    parser.add_argument('--visitor', choices=['enhanced'],
                        default='enhanced', help='Visitor para elementos da UI')

    # Parâmetros adicionais
    parser.add_argument('--provider', help='Provider para frontier models ou langchain/dspy')
    parser.add_argument('--api-key', help='API key para serviços remotos')

    args = parser.parse_args()
    return args


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

    # Configura componentes com base nos argumentos
    # configurator.set_llm(
    #     llm_type=args.llm, # "ollama", "huggingface", "dspy", "langchain", "frontier"
    #     model=args.model,
    #     base_url=args.base_url,
    #     provider=args.provider,
    #     api_key=args.api_key
    # )
    # configurator.set_strategy(args.strategy)  # "basic", "dspy", "single_action"
    # configurator.set_parser(args.parser)
    # configurator.set_visitor(args.visitor)

    # # DSPY
    configurator.set_llm(
        llm_type="dspy",  # "ollama", "huggingface", "dspy", "langchain", "frontier"
        model="llama3.2:3b",
        base_url="http://localhost:11434",
        provider="ollama",
        api_key=args.api_key
    )
    configurator.set_strategy("dspy")  # "basic", "dspy", "single_action"
    configurator.set_parser("droidbot")
    configurator.set_visitor("enhanced")

    # # OLLAMA
    # configurator.set_llm(
    #     llm_type="ollama",  # "ollama", "huggingface", "dspy", "langchain", "frontier"
    #     model="llama3.2:3b",
    #     base_url="http://localhost:11434",
    #     provider="ollama"
    # )
    # configurator.set_strategy("single_action")  # "basic", "dspy", "single_action"
    # configurator.set_parser("droidbot")
    # configurator.set_visitor("enhanced")

    # HUGGING FACE
    # configurator.set_llm(
    #     llm_type=HuggingFaceLLM.NAME,  # "ollama", "huggingface", "dspy", "langchain", "frontier"
    #     model=HuggingFaceLLM.LLAMA
    # )
    # configurator.set_strategy("single_action")  # "basic", "dspy", "single_action"
    # configurator.set_parser("droidbot")
    # configurator.set_visitor("enhanced")

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
    service = configurator.create_service()

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