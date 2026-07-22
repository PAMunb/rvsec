from typing import TypedDict, List, Annotated, Optional

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph

from rv_agent import RVAgentConfig
from rv_agent.core.device_interface import DeviceInterface
from rv_agent.core.screenshot_optimizer import ScreenshotOptimizer
from rv_agent.llm.tools.android_tools import initialize_tools, get_android_tools
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class MeuEstado(TypedDict):
    messages: Annotated[list, add_messages]
    screenshot: str
    screen_description: str

class MeuAgente:

    def __init__(self, config: RVAgentConfig, static_data: Optional[StaticAnalysisData]):
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.core.tmp_001",
            {CONTEXT_COMPONENT: "MeuAgente"}
        )

        # Initialize Android tools (raises on failure)
        # try:
        #     initialize_tools(config.device_id)
        #     self.tools = get_android_tools()
        #     self.logger.info(f"Initialized {len(self.tools)} Android tools")
        # except Exception as e:
        #     self.logger.error(f"Tool initialization failed: {e}")
        #     raise RuntimeError(f"Failed to initialize Android tools: {e}")

        self.config = config
        self.static_data = static_data

        self.device = DeviceInterface(config.device_id)
        self.screenshot_optimizer = ScreenshotOptimizer()
        self.llm = self._create_llm()
        self.parser = UIAutomator2Parser(DefaultTextVisitor)

        self.graph = self._build_graph()
        self.logger.info("LangGraph agent initialized successfully")

    def run(self):
        print("run ...")
        self.graph.invoke({"package": self.config.package_name})

    def init_app(self, state: MeuEstado):
        print("init_app")
        # TODO checa se o app esta no ar (tela atual), com uma tolerancia de 3 tentativas (para caso de tela de login, etc)
        # apos essas tentativas o app deve ser reiniciado
        # ou iniciar caso seja a primeira execucao
        self.logger.info(f"Initializing app: {self.config.package_name}")
        self.device.launch_app(self.config.package_name)
        return state

    def screenshot(self, state: MeuEstado):
        print("screenshot")
        self.logger.info("Taking screenshot...")
        screenshot_path = self.device.take_screenshot()
        self.logger.info(f"Screenshot taken: {screenshot_path}")
        self.logger.info(f"Optimizing screenshot...")
        # Optimize screenshot for vision model
        optimized_b64 = self.screenshot_optimizer.optimize(screenshot_path)
        self.logger.info(f"Screenshot optimized: {optimized_b64}")
        # self.logger.info(f"Screenshot optimized: {f"{optimized_b64[:50]}..." if len(optimized_b64) > 50 else optimized_b64}")
        if optimized_b64:
            print("guardou screenshot no state")
            return {"screenshot": optimized_b64}
        else:
            return {"screenshot": None}

    def describe_screen(self, state: MeuEstado):
        ui_state = self.device.get_current_ui_state()
        xml_dump = ui_state["xml"]
        print(f"static_data={static_data}")
        screen_description: ScreenDescription = self.parser.parse_screen({"hierarchy":xml_dump}, self.static_data)
        # screen_description: ScreenDescription = self.parser.parse(xml_dump, self.static_data)
        print(f"screen_description={screen_description}")
        exit(1)

        # TODO melhorar a forma como pega a atividade atual
        texto = f"Activity: {ui_state["current_package"]}.{ui_state["current_activity"]}\n"

        for item in screen_description.items:
            if "clickable" in item.view and item.view["clickable"]:
                print(f"item={item.base_description} :: view={item.view}")
                print(f" - actions={item.actions}")
                # TODO incluir [M] e [DM]
                reaches_mop = False
                directly_reaches_mop = False
                for action in item.actions:
                    if action.reaches_mop:
                        reaches_mop = True
                        print(">>>>>>>>>>>> reaches_mop")
                    if action.directly_reaches_mop:
                        directly_reaches_mop = True
                        print(">>>>>>>>>>>> directly_reaches_mop")
                        break
                reaches = " - [DM]" if directly_reaches_mop else "[M]" if reaches_mop else ""
                texto += f"{item.base_description}{reaches} - bbox={item.view["bounds"]}\n"

        print(f"\nTEXTO:\n{texto}")
        exit(1)

        return {"screen_description": texto}

    def describe_screenshot(self, state: MeuEstado):
        print("describe_screenshot")

        # Dimensões da imagem otimizada enviada para a LLM
        optimized_width = 724
        optimized_height = 1288

        prompt = f"""Analise detalhadamente o seguinte screenshot de um aplicativo Android.

IMPORTANTE - Dimensões da Imagem:
- A imagem que você está analisando tem {optimized_width}x{optimized_height} pixels
- Forneça coordenadas PRECISAS relativas a essa resolução

TAREFA:
1. Identifique TODOS os elementos clicáveis visíveis (botões, campos, etc)
2. Para CADA elemento, forneça:
   - Nome/texto do elemento
   - Coordenadas do CENTRO do elemento no formato: (x, y)
   - Bounding box no formato: x, y, width, height

FORMATO DA RESPOSTA:
Para cada elemento, use este formato EXATO:
- [NOME DO ELEMENTO]: center=(x, y), box=(x, y, width, height)

Exemplo:
- MESSAGE DIGEST: center=(362, 181), box=(8, 154, 708, 54)
- LOGIN BUTTON: center=(400, 600), box=(200, 575, 400, 50)

Seja PRECISO nas coordenadas, medindo cuidadosamente a posição na imagem de {optimized_width}x{optimized_height} pixels."""

        message_content = [{"type": "text", "text": prompt},
                           {
                               "type": "image_url",
                               "image_url": {"url": f"data:image/jpeg;base64,{state["screenshot"]}"}
                           }]
        messages = [
            SystemMessage("Você é um especialista em interfaces Android, descrevendo os componentes visuais e sua funcionalidade"),
            HumanMessage(content=message_content)
        ]

        response: AIMessage = self.llm.invoke(messages)
        print(f"content={response.content}")
        print(f"metadata={response.response_metadata}")
        print(f"usage={response.usage_metadata}")

        messages.append(response)

        return {"messages": messages}

    def mostrar_estado(self, state: MeuEstado):
        print("mostrar estado final: ")
        print(state)
        return state

    def _build_graph(self):
        builder = StateGraph(MeuEstado)
        builder.add_node("init_app", self.init_app)
        builder.add_node("screenshot", self.screenshot)
        builder.add_node("describe_screen", self.describe_screen)
        builder.add_node("describe_screenshot", self.describe_screenshot)
        builder.add_node("mostrar_estado", self.mostrar_estado)
        builder.add_edge(START, "init_app")
        builder.add_edge("init_app", "screenshot")
        builder.add_edge("screenshot", "describe_screen")
        builder.add_edge("describe_screen", "describe_screenshot")
        builder.add_edge("describe_screenshot", "mostrar_estado")
        builder.add_edge("mostrar_estado", END)                 # Usa a função de roteamento
        return builder.compile()

    def _create_llm(self):
        try:
            llm = ChatOllama(
                model=self.config.llm_model,
                base_url="http://localhost:11434", # TODO tornar configuravel
                temperature=self.config.llm_temperature,
                top_p=self.config.llm_top_p,
                top_k=self.config.llm_top_k,
                num_predict=self.config.llm_max_tokens
            )
            self.logger.info(f"LLM initialized: {self.config.llm_model}")
            return llm #.bind_tools(self.tools)
        except Exception as e:
            self.logger.error(f"LLM initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize LLM: {e}")


if __name__ == "__main__":
    import sys
    import logging
    import os

    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers for clean CLI output
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = os.path.join(screenshots_folder, apk)
    app = App(app_path=os.path.join(app_folder, apk))
    package = app.package_name

    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)
    # print(f"static_data={static_data}")

    config = RVAgentConfig(
        timeout=60,
        device_id="emulator-5554",
        package_name=package,
        llm_model="qwen-vision-tools-v1",
        llm_temperature=0.7,
        llm_top_p=0.9,
        llm_top_k=40,
        llm_max_tokens=4096
    )
    agent = MeuAgente(config, static_data=static_data)
    agent.run()