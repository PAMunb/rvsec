import logging
import sys
import os
import json

from rvandroid.app import App
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType
from rvandroid.parser.screen.visitor.model import ScreenItem
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvandroid.parser.screen.visitor.enhanced_visitor import EnhancedTextVisitor
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.static import static_analysis_parser


# Função auxiliar para ler estados do DroidBot
def read_droidbot_state(filename):
    with open(filename, 'r') as file:
        return json.load(file)


# Função auxiliar para ler dados XML do UIAutomator
def read_uiautomator_xml(filename):
    with open(filename, 'r') as file:
        return file.read()


# Exemplo 1: Usando o ParserFactory para criar um parser DroidBot com visitor básico
def tmp_001(screen_info, static_data):
    """
    Exemplo básico usando ParserFactory para criar um DroidBot parser com BasicTextVisitor.
    Mostra a descrição completa da tela com elementos e ações.
    """
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    # parser = ParserFactory.create(ParserType.DROIDBOT, DefaultTextVisitor)
    # parser = ParserFactory.create(ParserType.DROIDBOT, EnhancedTextVisitor)
    screen_description = parser.parse(screen_info, static_data)
    print(f"=== EXEMPLO 1: BasicTextVisitor com DroidBot ===")
    print(f"Activity: {screen_description.activity}")
    print(f"Elementos encontrados: {len(screen_description.items)}")
    print(f"Descrição da tela:\n{screen_description}")


# Exemplo 2: Usando um DefaultTextVisitor para descrições mais detalhadas
def tmp_002(screen_info, static_data):
    """
    Usando DefaultTextVisitor para descrições mais detalhadas dos elementos UI.
    Compara com o BasicTextVisitor do exemplo 1.
    """
    parser = ParserFactory.create(ParserType.DROIDBOT, DefaultTextVisitor)
    screen_description = parser.parse(screen_info, static_data)
    print(f"=== EXEMPLO 2: DefaultTextVisitor com DroidBot ===")
    print(f"Activity: {screen_description.activity}")
    print(f"Elementos encontrados: {len(screen_description.items)}")

    # Exibindo apenas os primeiros 3 itens para comparação
    print("Primeiros 3 elementos:")
    for i, item in enumerate(screen_description.items[:3]):
        print(f"Item {i + 1}: {item.base_description}")
        print(f"  Ações: {[action.text for action in item.actions]}")
        print()

    print(screen_description)


# Exemplo 3: Enhanced Visitor para descrição detalhada com análise adicional
def tmp_003(screen_info, static_data):
    """
    Usando EnhancedTextVisitor para obter informações detalhadas de UI com análise adicional
    como profundidade de hierarquia, tipo de layout, propósito de botões etc.
    """
    parser = ParserFactory.create(ParserType.DROIDBOT, EnhancedTextVisitor)
    screen_description = parser.parse(screen_info, static_data)
    print(f"=== EXEMPLO 3: EnhancedTextVisitor com DroidBot ===")
    print(f"Activity: {screen_description.activity}")
    print(f"Elementos encontrados: {len(screen_description.items)}")

    # O primeiro item normalmente contém informações estruturais da tela
    if screen_description.items:
        print(f"Visão geral da tela: {screen_description.items[0].base_description}")

    # Buscando por elementos seguros/sensíveis
    secure_items = []
    for item in screen_description.items:
        for action in item.actions:
            if action.reaches_mop or action.directly_reaches_mop:
                secure_items.append((item.base_description, action.text))

    if secure_items:
        print("\nElementos com operações sensíveis de segurança:")
        for desc, action in secure_items:
            print(f" - {desc}: {action}")
    else:
        print("\nNenhum elemento sensível de segurança identificado.")

    print(screen_description)


# Exemplo 4: Criar e usar um UIAutomator parser
def tmp_004(xml_data, static_data, activity_name=None):
    """
    Criando e usando um UIAutomator2Parser com dados XML.
    Mostra como processar hierarquia XML do UIAutomator.
    """
    # Cria parser para UIAutomator
    parser = ParserFactory.create(ParserType.UIAUTOMATOR)

    # Para UIAutomator, podemos usar o método parse diretamente com a string XML
    # Podemos opcionalmente fornecer o nome da atividade se disponível
    screen_description = parser.parse(xml_data, static_data, activity_name)

    print(f"=== EXEMPLO 4: UIAutomator2Parser ===")
    print(f"Activity: {screen_description.activity}")
    print(f"Elementos encontrados: {len(screen_description.items)}")

    # Exibindo informações sobre elementos clicáveis
    clickable_items = []
    for item in screen_description.items:
        for action in item.actions:
            if "CLICK" in action.text:
                clickable_items.append(item.base_description)
                break

    print(f"\nElementos clicáveis ({len(clickable_items)}):")
    for i, desc in enumerate(clickable_items[:5]):  # Mostrar apenas os primeiros 5
        print(f" - {desc}")
    if len(clickable_items) > 5:
        print(f"   ...e mais {len(clickable_items) - 5} elementos")


# Exemplo 5: Usando VisitorFactory para criar diferentes tipos de visitors
def tmp_005(screen_info, static_data):
    """
    Demonstra o uso do VisitorFactory para criar diferentes tipos de visitors.
    Compara as saídas dos diferentes tipos de visitors.
    """
    print(f"=== EXEMPLO 5: Comparando diferentes Visitors via VisitorFactory ===")
    visitor_types = ["basic", "default", "detailed"]
    parser_type = ParserType.DROIDBOT

    for visitor_type in visitor_types:
        # Usamos o VisitorFactory para obter a classe do visitor
        visitor_class = VisitorFactory.get_visitor_class(visitor_type)
        parser = ParserFactory.create(parser_type, visitor_class)
        screen_description = parser.parse(screen_info, static_data)

        print(f"\nVisitor: {visitor_type}")
        print(f"Elementos encontrados: {len(screen_description.items)}")
        if screen_description.items:
            print(f"Exemplo de descrição: {screen_description.items[0].base_description}")


# Exemplo 6: Criando um parser diretamente (sem factory)
def tmp_006(screen_info, static_data):
    """
    Criando instâncias de parser diretamente sem usar a factory.
    Útil quando você precisa de mais controle sobre a inicialização.
    """
    print(f"=== EXEMPLO 6: Criando parsers diretamente ===")

    # Criar DroidBotParser diretamente com DefaultTextVisitor
    droidbot_parser = DroidBotParser(DefaultTextVisitor)
    db_description = droidbot_parser.parse(screen_info, static_data)

    print(f"DroidBotParser com DefaultTextVisitor:")
    print(f"Activity: {db_description.activity}")
    print(f"Elementos encontrados: {len(db_description.items)}")

    # Exemplo de criação direta de UIAutomator2Parser
    # Comentado pois precisaria de dados XML para executar
    # uiautomator_parser = UIAutomator2Parser(DefaultTextVisitor)
    # ui_description = uiautomator_parser.parse(xml_data, static_data)
    # print(f"\nUIAutomator2Parser com DefaultTextVisitor:")
    # print(f"Activity: {ui_description.activity}")
    # print(f"Elementos encontrados: {len(ui_description.items)}")


# Exemplo 7: Extraindo ações e manipulando resultados do parser
def tmp_007(screen_info, static_data):
    """
    Manipulando o resultado do parser para extrair ações específicas.
    Mostra como navegar e usar a estrutura ScreenDescription.
    """
    parser = ParserFactory.create(ParserType.DROIDBOT, TextVisitor)
    screen_description = parser.parse(screen_info, static_data)

    print(f"=== EXEMPLO 7: Extraindo e manipulando ações ===")
    print(f"Activity: {screen_description.activity}")

    # Extraindo ações por tipo
    click_actions = []
    text_input_actions = []
    scroll_actions = []

    for item in screen_description.items:
        for action in item.actions:
            if "CLICK" in action.text:
                click_actions.append((item.base_description, action.text))
            elif "SET_TEXT" in action.text:
                text_input_actions.append((item.base_description, action.text))
            elif "SCROLL" in action.text:
                scroll_actions.append((item.base_description, action.text))

    print(f"\nAções de clique ({len(click_actions)}):")
    for desc, action in click_actions[:3]:  # Mostrar apenas os primeiros 3
        print(f" - {desc}: {action}")

    print(f"\nCampos de entrada de texto ({len(text_input_actions)}):")
    for desc, action in text_input_actions[:3]:
        print(f" - {desc}: {action}")

    print(f"\nAções de rolagem ({len(scroll_actions)}):")
    for desc, action in scroll_actions[:3]:
        print(f" - {desc}: {action}")


# Exemplo 8: Procurando por elementos específicos na tela
def tmp_008(screen_info, static_data):
    """
    Localiza elementos específicos na tela usando diferentes critérios.
    Útil para testes ou automação focada.
    """
    parser = ParserFactory.create(ParserType.DROIDBOT, TextVisitor)
    screen_description = parser.parse(screen_info, static_data)

    print(f"=== EXEMPLO 8: Buscando elementos específicos ===")

    # Busca por texto
    text_to_find = "login"  # Substitua pelo texto que você está procurando
    login_elements = []

    for item in screen_description.items:
        # Buscar no texto da descrição (case insensitive)
        if text_to_find.lower() in item.base_description.lower():
            login_elements.append(item)

    print(f"Elementos relacionados a '{text_to_find}': {len(login_elements)}")
    for i, item in enumerate(login_elements):
        print(f"{i + 1}. {item.base_description}")
        print(f"   Ações: {[action.text for action in item.actions]}")

    # Encontra elementos por propriedades específicas em node.data
    # Por exemplo, encontrar todos os campos de senha
    password_fields = []

    for item in screen_description.items:
        view_data = item.view
        # Verifica se é um campo de senha
        if view_data.get("is_password", False) or "password" in item.base_description.lower():
            password_fields.append(item)

    print(f"\nCampos de senha encontrados: {len(password_fields)}")
    for item in password_fields:
        print(f" - {item.base_description}")


# Exemplo 9: Usando visitor personalizado com foco em segurança
def tmp_009(screen_info, static_data):
    """
    Criando e usando um visitor personalizado com foco em segurança.
    Demonstra como você pode estender o sistema para necessidades específicas.
    """
    # Este é um exemplo conceitual. Em um caso real, você criaria uma subclasse completa.
    # Aqui, vamos usar o EnhancedTextVisitor existente e filtrar seus resultados.

    parser = ParserFactory.create(ParserType.DROIDBOT, EnhancedTextVisitor)
    screen_description = parser.parse(screen_info, static_data)

    print(f"=== EXEMPLO 9: Análise de segurança da tela ===")
    print(f"Activity: {screen_description.activity}")

    # Classificar elementos por nível de sensibilidade
    critical_elements = []
    sensitive_elements = []
    input_elements = []

    for item in screen_description.items:
        has_critical = False
        has_sensitive = False
        is_input = False

        for action in item.actions:
            if action.directly_reaches_mop:
                has_critical = True
            elif action.reaches_mop:
                has_sensitive = True

            if "SET_TEXT" in action.text:
                is_input = True

        if has_critical:
            critical_elements.append(item)
        elif has_sensitive:
            sensitive_elements.append(item)
        elif is_input:
            input_elements.append(item)

    print(f"\nElementos CRÍTICOS (acesso direto a operações protegidas): {len(critical_elements)}")
    for item in critical_elements:
        print(f" - {item.base_description}")

    print(f"\nElementos SENSÍVEIS (podem alcançar operações protegidas): {len(sensitive_elements)}")
    for item in sensitive_elements:
        print(f" - {item.base_description}")

    print(f"\nCampos de entrada (potencialmente sensíveis): {len(input_elements)}")
    for item in input_elements:
        print(f" - {item.base_description}")

    # Análise de segurança da tela
    risk_level = "Baixo"
    if len(critical_elements) > 0:
        risk_level = "Crítico"
    elif len(sensitive_elements) > 2:
        risk_level = "Alto"
    elif len(sensitive_elements) > 0 or len(input_elements) > 2:
        risk_level = "Médio"

    print(f"\nNível de risco da tela: {risk_level}")


# Exemplo 10: Comparando resultados entre DroidBot e UIAutomator
def tmp_010(droidbot_data, uiautomator_xml, static_data):
    """
    Compara os resultados entre os parsers DroidBot e UIAutomator para a mesma tela.
    Verifica quais elementos são detectados por ambos ou apenas por um deles.
    """
    print(f"=== EXEMPLO 10: Comparando DroidBot e UIAutomator ===")

    # Parsers com o mesmo tipo de visitor para comparação justa
    droidbot_parser = ParserFactory.create(ParserType.DROIDBOT, TextVisitor)
    uiautomator_parser = ParserFactory.create(ParserType.UIAUTOMATOR, TextVisitor)

    # Parse dos dados
    db_description = droidbot_parser.parse(droidbot_data, static_data)
    ui_description = uiautomator_parser.parse(uiautomator_xml, static_data)

    print(f"DroidBot - Elementos encontrados: {len(db_description.items)}")
    print(f"UIAutomator - Elementos encontrados: {len(ui_description.items)}")

    # Análise de elementos de interação comuns
    db_clickable = set()
    ui_clickable = set()

    for item in db_description.items:
        for action in item.actions:
            if "CLICK" in action.text:
                db_clickable.add(item.base_description)
                break

    for item in ui_description.items:
        for action in item.actions:
            if "CLICK" in action.text:
                ui_clickable.add(item.base_description)
                break

    common_elements = db_clickable.intersection(ui_clickable)
    only_db = db_clickable - ui_clickable
    only_ui = ui_clickable - db_clickable

    print(f"\nElementos clicáveis em comum: {len(common_elements)}")
    print(f"Elementos detectados apenas pelo DroidBot: {len(only_db)}")
    print(f"Elementos detectados apenas pelo UIAutomator: {len(only_ui)}")

    # Exibindo alguns exemplos
    if only_db:
        print("\nExemplos detectados apenas pelo DroidBot:")
        for desc in list(only_db)[:3]:
            print(f" - {desc}")

    if only_ui:
        print("\nExemplos detectados apenas pelo UIAutomator:")
        for desc in list(only_ui)[:3]:
            print(f" - {desc}")


def tmp_011(screen_info, static_data):
    """
    Usando uma subclasse personalizada do BasicTextVisitor para mostrar
    o texto dos botões em vez da classe
    """

    class CustomBasicVisitor(BasicTextVisitor):
        def visit_button(self, node):
            """
            Sobrescreve o método visit_button para mostrar o texto do botão em vez da classe
            """
            actions = self.get_possible_actions(node, self.counter)
            # Use o texto do botão se disponível, caso contrário use "Button"
            text = f"Botao \"{node.view_text if node.view_text else "sem texto"}\""
            item = ScreenItem(node.data, text, actions)
            self.items.append(item)
            self.window_info["interactive_elements"] += 1

    # Cria o parser com nosso visitor personalizado
    parser = ParserFactory.create(ParserType.DROIDBOT, CustomBasicVisitor)
    screen_description = parser.parse(screen_info, static_data)

    print(f"=== EXEMPLO 11: BasicTextVisitor Personalizado ===")
    print(f"Activity: {screen_description.activity}")

    # Exibe botões encontrados
    for item in screen_description.items:
        for action in item.actions:
            if "CLICK" in action.text:
                print(f"- {item.base_description}. Actions: {action.text}")
                break


# Função principal de execução dos exemplos
if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Iniciando exemplos de parsers...")

    # Definir caminhos para os arquivos
    apk = "cryptoapp.apk"
    screenshot_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/" + apk
    droidbot_info_file = screenshot_folder + "/004.state"
    uiautomator_xml_file = screenshot_folder + "/002.xml"  # Ajuste o caminho se necessário

    # Carregar dados
    screen_info = read_droidbot_state(droidbot_info_file)

    uiautomator_xml = None
    try:
        uiautomator_xml = read_uiautomator_xml(uiautomator_xml_file)
    except Exception as e:
        logging.warning(f"Não foi possível ler o arquivo XML do UIAutomator: {e}")

    # Carregar dados de análise estática
    app = App(os.path.join(screenshot_folder, apk))
    package = app.package_name
    static_data = static_analysis_parser.read_static_analysis_files(screenshot_folder, apk, package)

    # Executar os exemplos
    tmp_001(screen_info, static_data)
    # tmp_002(screen_info, static_data)
    # tmp_003(screen_info, static_data)
    #
    # if uiautomator_xml:
    #     tmp_004(uiautomator_xml, static_data)
    # else:
    #     logging.warning("Pulando exemplo 4 (UIAutomator) pois os dados XML não estão disponíveis")
    #
    # tmp_005(screen_info, static_data)
    # tmp_006(screen_info, static_data)
    # tmp_007(screen_info, static_data)
    # tmp_008(screen_info, static_data)
    # tmp_009(screen_info, static_data)
    #
    # if uiautomator_xml:
    #     tmp_010(screen_info, uiautomator_xml, static_data)
    # else:
    #     logging.warning("Pulando exemplo 10 (comparação) pois os dados XML não estão disponíveis")
    #
    # tmp_011(screen_info, static_data)