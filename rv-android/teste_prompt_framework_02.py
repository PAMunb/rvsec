#!/usr/bin/env python3

"""
RV-Android Prompt Framework Tutorial.

This file presents a comprehensive tutorial of the RV-Android prompt system,
demonstrating from basic concepts to advanced features, including:
- Framework initialization and configuration
- Creation of states and contexts
- Using templates and fragments
- Template inheritance and versioning
- Using different strategies
- Strategy registration and extension
- Integration with ComponentConfigurator
"""

import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.constants import PromptStrategyType, StateEntry, ScreenParserType
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.prompt.information.base_fragment import InformationFragment
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid.llm.prompt.information.fragments.ui_elements_fragment import UIElementsFragment
from rvandroid.llm.prompt.information.fragments.ui_pattern_fragment import UIPatternFragment
from rvandroid.llm.prompt.strategy.base_strategy import PromptStrategy
from rvandroid.llm.prompt.template.jinja_repository import Jinja2TemplateRepository
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.llm.service.memory_manager import MemoryManager
from rvandroid.llm.service.transition_manager import TransitionManager
from rvandroid.parser.screen.parser_factory import ParserFactory, ParserType
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.parser.static import static_analysis_parser
from rvandroid.util.logging.manager import LoggingManager


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def enrich_state(state, static_data: StaticAnalysisData, config: ComponentConfigurator, package_name: str):
    memory_manager = MemoryManager(
        app_package=package_name,
        static_data=static_data
    )
    transition_manager = TransitionManager(static_data)
    llm_service = LLMActionService(
        static_data=static_data,
        config=config,
        app_package=package_name
    )

    # Override service's managers with our instances for testing
    llm_service.memory_manager = memory_manager
    llm_service.transition_manager = transition_manager

    llm_service.pre_process_state(state)
    return state


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


# Função para criar um estado completo para uso no tutorial
def create_complete_tutorial_state(activity_name="MainActivity", package_name="com.example.testapp", 
                                  is_login=False, is_payment=False):
    """
    Cria um estado completo com todas as variáveis potencialmente necessárias
    para os templates, evitando erros de variáveis ausentes.
    """
    # Elementos básicos do estado
    state = {
        StateEntry.PACKAGE_NAME: package_name,
        StateEntry.ACTIVITY: f"{package_name}.{activity_name}",
        StateEntry.SCREEN_DESCRIPTION: f"Tela de {activity_name} com elementos simulados para tutorial."
    }
    
    # Adicionar informações de elementos UI
    ui_text = ""
    if "login" in activity_name.lower() or is_login:
        ui_text = """
ELEMENTOS DE UI:
- Campo de texto: Nome de usuário (id: username_field)
- Campo de texto: Senha (id: password_field)
- Botão: Login (id: login_button)
- Botão: Cancelar (id: cancel_button)
- Link: Esqueci minha senha (id: forgot_password)
        """
    elif "payment" in activity_name.lower() or "transfer" in activity_name.lower() or is_payment:
        ui_text = """
ELEMENTOS DE UI:
- Campo de texto: Valor (id: amount_field)
- Campo de texto: Destinatário (id: recipient_field)
- Dropdown: Tipo de transferência (id: transfer_type)
- Botão: Confirmar (id: confirm_button)
- Botão: Cancelar (id: cancel_button)
        """
    else:
        ui_text = """
ELEMENTOS DE UI:
- Botão: Continuar (id: continue_button)
- Botão: Voltar (id: back_button)
- Lista: Opções principais (id: main_options)
- Item 1: Perfil (id: profile_option)
- Item 2: Configurações (id: settings_option)
- Item 3: Ajuda (id: help_option)
        """
    
    state["ui_elements"] = ui_text
    
    # Adicionar histórico de ações para templates de batch
    state["action_history"] = [
        "Clique no botão 'Continuar'",
        "Preencheu o campo 'Nome'",
        "Rolou a tela para baixo"
    ]
    
    # Adicionar padrões de UI detectados
    state["ui_patterns"] = ["form", "list"]
    
    # Adicionar informações de orientação de transição
    state["transition_guidance"] = {
        "visit_count": 2,
        "recommended_actions": ["Preencher todos os campos", "Testar validação de entrada"],
        "avoidable_actions": ["Voltar sem salvar dados"]
    }
    
    # Adicionar informações estáticas
    state["static_context"] = """
CONTEXTO ESTÁTICO:
- Atividade implementa validação de entrada
- Tela faz parte do fluxo principal do aplicativo
- Existem 3 operações monitoradas nesta tela
    """
    
    # Adicionar dados de teste e monitoramento
    state["testing_history"] = [
        {"action": "Clique em 'Login'", "result": "Sucesso", "screen": "LoginScreen"},
        {"action": "Validação de campo vazio", "result": "Erro exibido", "screen": "LoginScreen"}
    ]
    
    # Informações de workflow para batch actions
    state["workflow_guidance"] = """
ORIENTAÇÃO DE FLUXO DE TRABALHO:
1. Complete todos os campos obrigatórios
2. Verifique validações de entrada
3. Teste casos especiais (valores limites)
4. Confirme a operação
    """
    
    # Informações para prompt de UI pattern
    state["detected_pattern"] = "form" if (is_login or is_payment) else "list"
    
    # Variáveis adicionais requeridas por templates específicos
    state["memory_insights"] = """
INSIGHTS DE MEMÓRIA DO APLICATIVO:
- 2 telas visitadas anteriormente nesta sessão
- Padrão comum de navegação: Login -> Home -> Esta tela
- Telas mais visitadas: Home (5x), Settings (2x), Login (3x)
    """
    
    # Adicionar informações sobre a execução de teste
    state["testing_context"] = {
        "session_duration": "00:15:23",
        "coverage": {"activities": "45%", "code": "38%", "transitions": "29%"},
        "monitored_operations_found": 7,
        "focus_areas": ["input_validation", "permission_usage", "data_handling"]
    }
    
    # Adicionar metadados de aplicativo
    state["app_metadata"] = {
        "app_name": package_name.split(".")[-1].capitalize(),
        "version": "1.2.3",
        "sdk_target": 33,
        "permissions": ["INTERNET", "CAMERA", "READ_EXTERNAL_STORAGE"]
    }
    
    # Variáveis adicionais que possam ser usadas por qualquer template
    state["additional_guidelines"] = "Priorize testar validação de entrada e segurança."
    state["exploration_status"] = "Em progresso - 45% do aplicativo explorado"
    state["security_considerations"] = "Verifique uso seguro de APIs de criptografia"
    
    return state


###################################################################################
# SEÇÃO 1: CONCEITOS BÁSICOS
###################################################################################

def tutorial_section_1():
    """
    Seção 1: Conceitos Básicos do Framework de Prompts.
    
    Esta seção demonstra:
    - A inicialização básica do PromptFramework
    - Criação de um estado simples
    - Geração de um prompt básico
    - Estrutura de mensagens LLM
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 1: CONCEITOS BÁSICOS DO FRAMEWORK DE PROMPTS")
    print("=" * 80)

    print("\n1.1: Inicialização do Framework")
    print("-" * 40)

    # O PromptFramework pode ser criado diretamente usando o método estático create()
    # que inicializa todos os componentes necessários com valores padrão
    print("Criando o framework com configuração padrão...")

    # Inicializando o configurador
    configurator = ComponentConfigurator()
    
    # Definindo o tipo de LLM e a estratégia
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.LLAMA,  # Utilizamos o modelo Llama3 disponível via Ollama
        base_url="http://localhost:11434"  # URL local do servidor Ollama
    )
    configurator.set_strategy(PromptStrategyType.STANDARD)
    
    # Criando o framework com nossa configuração
    framework = PromptFramework.create(configurator)

    print("Framework inicializado com sucesso.")
    print("Componentes principais:")
    print(f"- Information Manager: {framework.information_manager.__class__.__name__}")
    print(f"- Template Repository: {framework.template_repository.__class__.__name__}")
    print(f"- Component Configurator: {framework.config.__class__.__name__}")

    # Criação de um estado completo para o tutorial
    print("\n1.2: Criação de um Estado Completo para o Tutorial")
    print("-" * 40)

    # Criamos um estado completo com todas as variáveis que os templates podem precisar
    print("Criando um estado completo para demonstração...")
    basic_state = create_complete_tutorial_state("MainActivity", "com.example.testapp")

    print("\nEstado criado com os seguintes dados principais:")
    for key in [StateEntry.PACKAGE_NAME, StateEntry.ACTIVITY, StateEntry.SCREEN_DESCRIPTION]:
        print(f"- {key}: {basic_state[key]}")
    
    print("\nO estado também inclui outros dados necessários para os templates:")
    print("- ui_elements: Informações sobre elementos de UI")
    print("- action_history: Histórico de ações anteriores")
    print("- transition_guidance: Orientações de navegação")
    print("- static_context: Informações estáticas sobre a tela")
    print("- detected_pattern: Padrão de UI identificado")

    # Geração de um prompt simples
    print("\n1.3: Geração de um Prompt Básico")
    print("-" * 40)

    # Gerando o prompt real usando o framework
    print("Gerando prompt com o framework...")
    messages = framework.generate_prompt(basic_state)
    
    # Exibir mensagens geradas
    print(f"\nPrompt gerado com {len(messages)} mensagens:")
    
    for i, msg in enumerate(messages):
        print(f"\nMensagem {i+1} - Papel: {msg.role}")
        for content in msg.content:
            # Limitar a quantidade de texto exibida para não sobrecarregar o console
            text = content.text
            if len(text) > 300:
                text = text[:300] + "... (texto truncado)"
            print(f"Conteúdo: {text}")

    print("\n1.4: Prompt Framework Structure")
    print("-" * 40)
    print("""
The Prompt Framework is composed of three main layers:

1. Information Collection (InformationManager and Fragments)
   - Responsible for extracting and organizing information from the current state
   - Each fragment specializes in a specific type of information
   - Fragments can be enabled/disabled as needed

2. Template System (Jinja2TemplateRepository)
   - Manages the structure of LLM messages
   - Supports template inheritance and versioning
   - Uses Jinja2 for advanced template rendering

3. Prompt Strategies (via ComponentConfigurator)
   - Defines how prompts are generated for specific use cases
   - Integrates information and templates to create messages
   - Allows customization of prompt generation behavior

Strategies are now integrated with ComponentConfigurator, which serves as
the central configuration point of the system, avoiding duplicate registration.
""")


###################################################################################
# SEÇÃO 2: CONFIGURAÇÃO AVANÇADA
###################################################################################

def tutorial_section_2():
    """
    Seção 2: Configuração Avançada.
    
    Esta seção demonstra:
    - Configuração personalizada do framework
    - Uso do ComponentConfigurator
    - Seleção de estratégias
    - Passagem de contexto adicional
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 2: CONFIGURAÇÃO AVANÇADA")
    print("=" * 80)

    print("\n2.1: Configuração Personalizada com ComponentConfigurator")
    print("-" * 40)

    # Inicializando o configurador para esta demonstração
    configurator = ComponentConfigurator()

    # Configuração de LLM com parâmetros personalizados
    print("Configurando LLM com parâmetros personalizados...")
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,  # Tipo de modelo (ollama, huggingface, etc.)
        model="llama3",  # Nome do modelo específico
        base_url="http://localhost:11434",  # URL base para API
        temperature=0.7,  # Temperatura (criatividade)
        max_tokens=2000  # Máximo de tokens na resposta
    )

    # Configuração de estratégia
    print("Configurando estratégia para processamento em lote...")
    configurator.set_strategy(PromptStrategyType.BATCH_ACTION)  # Usar estratégia de batch
    
    # Criando o framework com nossa configuração personalizada
    framework = PromptFramework.create(configurator)
    
    print("Framework criado com configuração personalizada.")
    print(f"Detalhes da configuração:")
    print(f"- Estratégia: {configurator.llm_config.strategy_type}")
    print(f"- Modelo LLM: {configurator.llm_config.model_name}")
    print(f"- Temperatura: {configurator.llm_config.temperature}")
    print(f"- Tokens máximos: {configurator.llm_config.max_tokens}")

    print("\n2.2: Passagem de Contexto Adicional")
    print("-" * 40)

    # Criação de um estado específico para demonstração de transferência bancária
    bank_state = create_complete_tutorial_state(
        activity_name="TransferActivity", 
        package_name="com.example.bankapp", 
        is_payment=True
    )
    
    # O contexto adicional fornece informações específicas para o prompt
    # que não são parte do estado da aplicação, mas são relevantes para a geração
    context = {
        "exploration_focus": "monitored_operations",  # Foco em operações monitoradas
        "testing_goal": "vulnerabilities",  # Objetivo do teste
        "special_instructions": "Dê atenção especial a validação de entrada e verificação de autenticação",
        "security_level": "high"
    }

    print("Estado de transferência bancária - principais campos:")
    main_fields = [StateEntry.PACKAGE_NAME, StateEntry.ACTIVITY, StateEntry.SCREEN_DESCRIPTION]
    for key in main_fields:
        print(f"- {key}: {bank_state[key]}")
    
    print("\nElementos de UI incluídos:")
    print(bank_state["ui_elements"][:200] + "..." if len(bank_state["ui_elements"]) > 200 else bank_state["ui_elements"])

    print("\nContexto adicional:")
    for key, value in context.items():
        print(f"- {key}: {value}")

    # Gerar prompt com contexto adicional usando o framework real
    print("\nGerando prompt com contexto adicional...")
    try:
        messages = framework.generate_prompt(bank_state, context)
        
        print(f"\nPrompt gerado com {len(messages)} mensagens:")
        for i, msg in enumerate(messages):
            print(f"\nMensagem {i+1} - Papel: {msg.role}")
            for content in msg.content:
                # Limitar a quantidade de texto exibida para não sobrecarregar o console
                text = content.text
                if len(text) > 300:
                    text = text[:300] + "... (texto truncado)"
                print(f"Conteúdo: {text}")
    except Exception as e:
        print(f"Erro ao gerar prompt: {e}")
        print("Nota: Em um ambiente de produção, certifique-se de que todos os templates necessários estão disponíveis.")
        print("Para este tutorial, mostraremos apenas o processo de configuração.")

    print("\n2.3: Seleção Dinâmica de Estratégias")
    print("-" * 40)

    # É possível alterar a estratégia em tempo de execução através do configurator
    print("Alterando estratégia para STANDARD...")
    configurator.set_strategy(PromptStrategyType.STANDARD)
    
    # Criando um novo framework com a estratégia atualizada
    updated_framework = PromptFramework.create(configurator)
    
    print(f"Framework atualizado:")
    print(f"- Nova estratégia: {configurator.llm_config.strategy_type}")
    
    # Tentar gerar um novo prompt com a estratégia padrão
    print("\nGerando prompt com a estratégia padrão...")
    try:
        new_messages = updated_framework.generate_prompt(bank_state, context)
        
        print(f"\nNovo prompt gerado com {len(new_messages)} mensagens:")
        for i, msg in enumerate(new_messages):
            print(f"\nMensagem {i+1} - Papel: {msg.role}")
            for content in msg.content:
                # Limitar a quantidade de texto exibida
                text = content.text
                if len(text) > 300:
                    text = text[:300] + "... (texto truncado)"
                print(f"Conteúdo: {text}")
    except Exception as e:
        print(f"Erro ao gerar prompt com nova estratégia: {e}")
        print("Observe que cada estratégia pode requerer templates específicos ou fragmentos de informação.")
        print("Na implementação real, certifique-se de que todos os componentes necessários estão disponíveis.")


###################################################################################
# SEÇÃO 3: SISTEMA DE TEMPLATES
###################################################################################

def tutorial_section_3():
    """
    Seção 3: Sistema de Templates e Fragmentos.
    
    Esta seção demonstra:
    - Como funcionam os templates XML com Jinja2
    - Herança de templates
    - Uso de fragmentos
    - Versionamento de templates
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 3: SISTEMA DE TEMPLATES E FRAGMENTOS")
    print("=" * 80)

    print("\n3.1: Estrutura de Templates XML com Jinja2")
    print("-" * 40)

    # Inicialização do repositório de templates para demonstração
    template_repo = Jinja2TemplateRepository()
    print(f"Diretório base de templates: {template_repo.template_dir}")
    print(f"Diretório de fragmentos: {template_repo.fragment_dir}")
    
    # Implementação simplificada para listar templates disponíveis
    # Isso substitui o método inexistente 'get_available_templates()'
    import os
    template_dir = template_repo.template_dir
    
    if os.path.exists(template_dir):
        available_templates = [f.replace('.xml', '') for f in os.listdir(template_dir) 
                             if f.endswith('.xml') and os.path.isfile(os.path.join(template_dir, f))]
    else:
        available_templates = ["standard_modular", "batch_action_modular", "security_focus", "exploration"]
    
    print(f"\nTemplates disponíveis no sistema ({len(available_templates)}):")
    for template in available_templates[:5]:  # Mostrar os primeiros 5 para não sobrecarregar
        print(f"- {template}")
    if len(available_templates) > 5:
        print(f"...e mais {len(available_templates) - 5} templates")

    # Os templates são armazenados em arquivos XML com sintaxe Jinja2 em seções CDATA
    print("""
O sistema de templates usa arquivos XML para definir a estrutura do prompt:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<template name="example_template" version="1.0">
  <metadata>
    <description>Template de exemplo</description>
    <created>2025-05-06</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>ui_elements</required>
    <optional>additional_guidelines</optional>
  </variables>
  <roles>
    <system><![CDATA[
      Você é um assistente de teste para Android.
      
      {% if ui_elements %}
      Elementos na tela:
      {{ ui_elements }}
      {% endif %}
      
      {% include "standard_guidelines" %}
    ]]></system>
    <user><![CDATA[
      Analise esta tela: {{ activity }}
      
      {% if additional_guidelines %}
      {{ additional_guidelines }}
      {% endif %}
    ]]></user>
  </roles>
</template>
```

Elementos importantes dos templates:
- <metadata>: Informações sobre o template (descrição, autor, data)
- <variables>: Define variáveis obrigatórias e opcionais
- <roles>: Define o conteúdo para cada role (system, user, assistant)
- Sintaxe Jinja2: 
  - {{ variable }}: Para substituição de variáveis
  - {% if condition %}: Para lógica condicional
  - {% include "fragment" %}: Para incluir fragmentos
""")

    print("\n3.2: Demonstração Real de Template")
    print("-" * 40)
    
    # Template preferido para demonstração
    template_name = available_templates[0] if available_templates else "standard_modular"
    print(f"Analisando um template real: '{template_name}'")
    
    # Criar estado completo para o template
    demo_state = create_complete_tutorial_state("LoginActivity", "com.example.demoapp", is_login=True)
    
    # Gerar mensagens com o template
    try:
        print("Gerando mensagens a partir do template com estado completo...")
        messages = template_repo.create_messages(template_name, demo_state)
        
        print(f"\nGerado {len(messages)} mensagens a partir do template '{template_name}':")
        for i, msg in enumerate(messages):
            # Verificar o tipo do objeto de mensagem (pode variar dependendo da implementação)
            if hasattr(msg, 'role'):
                role = msg.role
                if hasattr(msg, 'content'):
                    content_list = msg.content
                    print(f"\nMensagem {i+1} - Papel: {role}")
                    for content_item in content_list:
                        if hasattr(content_item, 'text'):
                            text = content_item.text
                            if len(text) > 300:
                                text = text[:300] + "... (texto truncado)"
                            print(f"Conteúdo: {text}")
            else:
                # Tratamento alternativo se a estrutura for diferente
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                print(f"\nMensagem {i+1} - Papel: {role}")
                if len(content) > 300:
                    content = content[:300] + "... (texto truncado)"
                print(f"Conteúdo: {content}")
                
    except Exception as e:
        print(f"Erro ao renderizar template: {e}")
        print("Gerando uma mensagem de exemplo para demonstração:")
        
        # Criação de mensagem de demonstração caso o template real falhe
        print("\nExemplo de mensagem que seria gerada:")
        print("Papel: system")
        print("Conteúdo: Você é um assistente de teste de aplicativo Android especializado em análise de segurança e teste de interface.\n")
        print("Papel: user")
        print("Conteúdo: Analise a tela de login e sugira ações de teste relevantes para validação de entrada e segurança.")

    print("\n3.3: Herança de Templates")
    print("-" * 40)

    # Herança permite que templates herdem características de templates base
    print("""
O sistema suporta herança de templates usando o atributo "extends":

Template Base (system_base.xml):
```xml
<template name="system_base" version="1.0">
  <roles>
    <system><![CDATA[
      {% block system_intro %}
      Você é um assistente de teste Android.
      {% endblock %}
      
      {% block instructions %}
      Sua tarefa é analisar a tela atual.
      {% endblock %}
    ]]></system>
  </roles>
</template>
```

Template Derivado (specialized_template.xml):
```xml
<template name="specialized_template" version="1.0" extends="system_base">
  <roles>
    <system><![CDATA[
      {% extends "system_base" %}
      
      {% block instructions %}
      Sua tarefa é encontrar vulnerabilidades de segurança na tela atual.
      {% endblock %}
    ]]></system>
    <user><![CDATA[
      Analise esta tela: {{ activity }}
    ]]></user>
  </roles>
</template>
```

Benefícios da herança:
- Reutilização de código comum entre templates
- Consistência entre templates relacionados
- Facilita a manutenção (alterações no template base são refletidas nos derivados)
- Permite especialização gradual de templates
""")

    print("\n3.4: Fragmentos e Inclusão")
    print("-" * 40)

    # Vamos listar os fragmentos disponíveis no sistema real
    try:
        # Em um sistema real, poderíamos obter os fragmentos assim:
        # available_fragments = template_repo.get_available_fragments()
        # Como essa função pode não existir, vamos simular os resultados:
        
        # Configuramos um framework para ver os fragmentos que ele usa
        configurator = ComponentConfigurator()
        framework = PromptFramework.create(configurator)
        repo = framework.template_repository
        
        print("Demonstrando o sistema de fragmentos...")
        print("Estrutura típica de um fragmento XML:")
        
        print("""
<fragment name="standard_guidelines">
  <![CDATA[
REGRAS IMPORTANTES:
1. Priorize explorar áreas novas do aplicativo
2. Teste entradas de dados com valores limites
3. Verifique tratamento de erros e validações
  ]]>
</fragment>
""")
        
        print("Uso em templates:")
        print("""
Em um template XML, os fragmentos são incluídos com a diretiva:

{% include "nome_do_fragmento" %}

Exemplos de inclusão condicional e dinâmica:

{% if ui_patterns %}
  {% for pattern in ui_patterns %}
    {% include "ui_patterns/" + pattern %}
  {% endfor %}
{% endif %}
""")
    except Exception as e:
        print(f"Erro ao demonstrar fragmentos: {e}")

    print("\n3.5: Versionamento de Templates")
    print("-" * 40)

    # O versionamento permite controlar mudanças nos templates
    print("""
Os templates suportam versionamento através do atributo "version":

```xml
<template name="security_template" version="1.2">
  <!-- conteúdo do template -->
</template>
```

O sistema de templates:
- Registra a versão no carregamento
- Permite carregar múltiplas versões do mesmo template
- Facilita rollbacks para versões anteriores se necessário
- Ajuda a rastrear a evolução dos templates ao longo do tempo

Isso é particularmente útil ao desenvolver e testar variações de templates.
""")

    print("\n3.6: Relação entre Templates e Fragmentos")
    print("-" * 40)

    # Uma explicação adicional sobre a arquitetura do sistema de templates
    print("""
O sistema de templates e fragmentos está estruturado hierarquicamente:

1. Jinja2TemplateRepository
   - Gerencia todos os templates e fragmentos
   - Carrega arquivos de template e fragmento dos diretórios configurados
   - Resolve referências entre templates (herança) e fragmentos (inclusão)

2. Templates XML
   - Definem a estrutura geral das mensagens para o LLM
   - Podem estender outros templates (herança)
   - Incluem fragmentos para conteúdo compartilhado
   - Contêm espaços reservados para variáveis

3. Fragmentos XML
   - Blocos reutilizáveis de conteúdo
   - Organizados em categorias (sistema, usuário, padrões UI)
   - Podem ser incluídos em qualquer template
   - Facilitam a manutenção e consistência

O processamento ocorre em várias etapas:
1. Carregamento dos templates e fragmentos
2. Resolução de herança entre templates
3. Resolução de inclusões de fragmentos
4. Substituição de variáveis
5. Processamento de condicionais e loops
6. Geração das mensagens finais
""")


###################################################################################
# SEÇÃO 4: SISTEMA DE INFORMAÇÕES E FRAGMENTOS
###################################################################################

def tutorial_section_4():
    """
    Seção 4: Sistema de Informações e Fragmentos.
    
    Esta seção demonstra:
    - Como funcionam os fragmentos de informação
    - Diferença entre fragmentos de template e fragmentos de informação
    - Criação de fragmentos personalizados
    - Prioridade e ordem de fragmentos
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 4: SISTEMA DE INFORMAÇÕES E FRAGMENTOS")
    print("=" * 80)

    print("\n4.1: Fragmentos de Informação vs Fragmentos de Template")
    print("-" * 40)

    # Explicação sobre a diferença entre os dois tipos de fragmentos
    print("""
É importante entender a diferença entre dois conceitos relacionados:

1. Fragmentos de Template:
   - Blocos de texto reutilizáveis em templates
   - Armazenados em arquivos XML
   - Incluídos nos templates usando {% include "nome_fragmento" %}
   - Gerenciados pelo Jinja2TemplateRepository

2. Fragmentos de Informação (Information Fragments):
   - Classes Python que extraem ou processam informações do estado
   - Implementam a interface InformationFragment
   - Geram conteúdo dinâmico baseado no estado atual
   - Gerenciados pelo InformationManager
   - Exemplos: UIElementsFragment, MonitoredOperationsFragment

A relação entre eles:
- Fragmentos de informação GERAM dados dinâmicos
- Fragmentos de template FORMATAM esses dados em texto
- As estratégias conectam os dois sistemas
""")

    print("\n4.2: Demonstração Real dos Fragmentos de Informação")
    print("-" * 40)

    # Criação de um gerenciador de informações real
    info_manager = InformationManager()

    # Registrar alguns fragmentos padrão
    fragments = [
        UIElementsFragment(),
        UIPatternFragment(),
        MonitoredOperationsFragment()
    ]
    info_manager.register_fragments(fragments)
    
    # Guardar referência aos fragmentos registrados para uso posterior
    # Isso nos permite acessar os fragmentos sem depender da estrutura interna do InformationManager
    registered_fragments = fragments.copy()

    print(f"Information Manager inicializado com {len(fragments)} fragmentos:")
    for fragment in fragments:
        print(f"- {fragment.name} (prioridade: {fragment.priority})")

    # Criar um estado básico para testar os fragmentos
    test_state = {
        StateEntry.PACKAGE_NAME: "com.example.testapp",
        StateEntry.ACTIVITY: "com.example.testapp.MainActivity",
        StateEntry.SCREEN_DESCRIPTION: "Tela de login com campos de usuário e senha"
    }

    test_context = {
        "exploration_focus": "user_interface"
    }

    # Demonstrar como um fragmento gera conteúdo a partir do estado
    print("\nDemonstrando geração de informação a partir do UIElementsFragment:")
    try:
        ui_fragment = UIElementsFragment()
        if ui_fragment.should_include(test_state, test_context):
            ui_content = ui_fragment.generate(test_state, test_context)
            print("\nConteúdo gerado:")
            if len(ui_content) > 300:
                print(ui_content[:300] + "... (texto truncado)")
            else:
                print(ui_content)
        else:
            print("O fragmento decidiu não incluir informações baseado no estado/contexto.")
    except Exception as e:
        print(f"Erro ao gerar conteúdo do fragmento: {e}")
    
    # Consulta através do InformationManager
    print("\nConsultando informações via InformationManager:")
    try:
        # Implementação alternativa do método get_information para o tutorial
        # Este método está sendo implementado aqui porque o método original pode não existir
        def get_information(manager, fragment_name, state, context=None):
            # Usamos o registered_fragments em vez de tentar acessar manager._fragments
            for fragment in registered_fragments:
                if fragment.name == fragment_name and fragment.should_include(state, context):
                    return fragment.generate(state, context)
            return None
        
        # Usar esta implementação alternativa
        ui_info = get_information(info_manager, "ui_elements", test_state, test_context)
        if ui_info:
            print("\nInformação de elementos UI recuperada via manager:")
            if len(ui_info) > 300:
                print(ui_info[:300] + "... (texto truncado)")
            else:
                print(ui_info)
        else:
            print("Nenhuma informação de UI disponível para este estado/contexto.")
    except Exception as e:
        print(f"Erro ao consultar informações: {e}")

    print("\nEstrutura básica de um fragmento de informação:")
    print("""
```python
class ExampleFragment(InformationFragment):
    def __init__(self, name: str = "example", priority: int = 100):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        # Extrair e processar informações do estado
        activity = state.get(StateEntry.ACTIVITY, "unknown")
        return f"Informação processada para atividade: {activity}"
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        # Decidir se este fragmento deve ser incluído
        # Baseado em critérios como o tipo de tela, contexto, etc.
        return True
```

Cada fragmento:
1. Tem um nome único e nível de prioridade
2. Implementa método `generate()` para processar o estado
3. Implementa método `should_include()` para decidir quando incluir
4. É processado pelo InformationManager em ordem de prioridade
""")

    print("\n4.3: Criação e Uso de um Fragmento de Informação Personalizado")
    print("-" * 40)

    # Implementação de um fragmento personalizado
    class CustomMonitoredOperationsFragment(InformationFragment):
        """Demonstração de fragmento personalizado que analisa informações de operações monitoradas."""

        def __init__(self, name: str = "monitored_ops_info", priority: int = 200):
            super().__init__(name, priority)

        def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
            """Gera informações sobre operações monitoradas com base no estado e contexto."""
            activity = state.get(StateEntry.ACTIVITY, "unknown")

            # Análise fictícia baseada na atividade
            if "login" in activity.lower():
                return """
ANÁLISE DE OPERAÇÕES MONITORADAS:
- Tela de login identificada - verificar manipulação adequada de credenciais
- Verificar validação de entrada nos campos de login
- Verificar inicialização adequada do gerenciamento de sessão
"""
            elif "payment" in activity.lower() or "transfer" in activity.lower():
                return """
ANÁLISE DE OPERAÇÕES MONITORADAS:
- Transação financeira detectada - alta prioridade para monitoramento
- Verificar validação adequada da transação
- Verificar validação de entrada para valores e destino da transação
- Verificar sequência de autenticação adequada
"""
            else:
                return """
ANÁLISE DE OPERAÇÕES MONITORADAS:
- Verificar validação de entrada nos campos visíveis
- Verificar padrões adequados de uso de API
- Testar manipulação de dados entre telas
"""

        def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
            """Determina se este fragmento deve ser incluído na geração do prompt."""
            # Incluir apenas se o contexto estiver focado em operações monitoradas
            if context:
                focus = context.get("exploration_focus", "")
                goal = context.get("testing_goal", "")
                return "monitored_operations" in focus or "api_usage" in goal
            return False

    # Registrando o fragmento personalizado no manager e na nossa lista local
    custom_fragment = CustomMonitoredOperationsFragment()
    info_manager.register_fragment(custom_fragment)
    registered_fragments.append(custom_fragment)  # Adicionamos à nossa lista local
    print("Fragmento personalizado registrado no InformationManager")
    
    # Demonstração do uso do fragmento personalizado
    print("\nTestando o fragmento personalizado:")

    # Estado e contexto para teste
    test_state_login = {
        StateEntry.PACKAGE_NAME: "com.example.bankapp",
        StateEntry.ACTIVITY: "com.example.bankapp.LoginActivity"
    }

    test_context_security = {
        "exploration_focus": "monitored_operations",
        "testing_goal": "api_usage"
    }

    # Consulta através do Information Manager para o novo fragmento
    try:
        # Usando a mesma implementação alternativa definida anteriormente
        sec_info = get_information(info_manager, "monitored_ops_info", test_state_login, test_context_security)
        if sec_info:
            print("\nInformação de operações monitoradas gerada pelo fragmento personalizado:")
            print(sec_info)
        else:
            print("Nenhuma informação de segurança disponível para este estado/contexto.")
    except Exception as e:
        print(f"Erro ao consultar informações do fragmento personalizado: {e}")

    print("\n4.4: Integração com o Framework Real")
    print("-" * 40)
    
    # Demonstrando a integração com o framework completo
    try:
        # Criar configurador e framework
        configurator = ComponentConfigurator()
        configurator.set_strategy(PromptStrategyType.STANDARD)
        framework = PromptFramework.create(configurator)
        
        # Registrar nosso fragmento personalizado no framework
        custom_fragment = CustomMonitoredOperationsFragment()
        framework.register_information_fragment(custom_fragment)
        
        print("Fragmento personalizado registrado no framework")
        
        # Em vez de tentar acessar propriedades internas, vamos registrar um contador simples
        # para manter o controle de quantos fragmentos foram registrados
        fragment_counter = 0
        
        # Função de registro personalizada para contar os fragmentos
        def count_fragment_registration(fragment):
            nonlocal fragment_counter
            fragment_counter += 1
            # Também executa o registro real
            framework.register_information_fragment(fragment)
        
        # Registrar fragmentos padrão e contar o total
        count_fragment_registration(UIElementsFragment())
        count_fragment_registration(UIPatternFragment())
        count_fragment_registration(MonitoredOperationsFragment())
        count_fragment_registration(custom_fragment)
        
        # Registrar mais alguns fragmentos de exemplo
        count_fragment_registration(InformationFragment("perf_stats", 150))
        count_fragment_registration(InformationFragment("navigation_tips", 120))
        count_fragment_registration(InformationFragment("testing_focus", 110))
        
        print(f"Total de fragmentos no framework: {fragment_counter}")
        
        # Demonstrar uma geração de prompt que utilizará os fragmentos
        print("\nGerando um prompt com o framework que utiliza os fragmentos de informação:")
        
        # Estado e contexto completos com foco em operações monitoradas
        security_state = create_complete_tutorial_state(
            activity_name="PaymentActivity", 
            package_name="com.example.bankapp", 
            is_payment=True
        )
        
        security_context = {
            "exploration_focus": "monitored_operations",
            "testing_goal": "api_usage"
        }
        
        # Gerar prompt usando o framework
        try:
            messages = framework.generate_prompt(security_state, security_context)
            print(f"\nPrompt gerado com {len(messages)} mensagens incluindo informações de fragmentos.")
            
            # Exibir um resumo das mensagens (limitando o tamanho para não sobrecarregar)
            for i, msg in enumerate(messages):
                print(f"\nMensagem {i+1} - Papel: {msg.role}")
                for content in msg.content:
                    text = content.text
                    if len(text) > 200:
                        text = text[:200] + "... (texto truncado)"
                    print(f"Conteúdo: {text}")
        except Exception as e:
            print(f"Erro ao gerar prompt completo: {e}")
            print("Isso é esperado em ambiente de desenvolvimento sem todos os componentes configurados")
            
            # Gerar um exemplo de mensagem para demonstrar o conceito
            print("\nExemplo conceitual do que seria gerado:")
            print("Papel: system")
            print("Conteúdo: Você é um assistente de teste Android focado em operações monitoradas.")
            print("Papel: user")
            print("Conteúdo: Analise esta tela de pagamento e identifique possíveis problemas de segurança.")
    except Exception as e:
        print(f"Erro ao configurar framework: {e}")
        print("Fornecendo uma explicação conceitual do processo de integração:")
        print("""
1. O framework é inicializado com seus componentes básicos
2. Fragmentos personalizados são registrados no InformationManager
3. O framework gera prompts consultando esses fragmentos conforme necessário
4. Os fragmentos fornecem informações específicas para cada template
        """)

    print("\n4.5: Fluxo de Processamento dos Fragmentos de Informação")
    print("-" * 40)

    print("""
O fluxo completo de processamento de fragmentos de informação:

1. O PromptFramework recebe uma solicitação de geração de prompt
2. A estratégia selecionada (ex: StandardStrategy) é executada
3. A estratégia determina quais variáveis são necessárias para o template
4. O InformationManager é solicitado a fornecer essas informações
5. Para cada variável:
   a. O InformationManager identifica os fragmentos relevantes
   b. Cada fragmento decide se deve ser incluído (should_include)
   c. Fragmentos incluídos são executados em ordem de prioridade
   d. O conteúdo gerado é agregado para formar o valor da variável
6. Os valores de variáveis são passados para o template
7. O template é renderizado com as variáveis
8. As mensagens finais são retornadas

Este processo permite:
- Modularidade na coleta de informações
- Priorização flexível de diferentes tipos de informação
- Inclusão condicional baseada no estado e contexto
- Extensibilidade através de novos fragmentos
""")


###################################################################################
# SEÇÃO 5: ESTRATÉGIAS DE PROMPT
###################################################################################

def tutorial_section_5():
    """
    Seção 5: Estratégias de Prompt.
    
    Esta seção demonstra:
    - O papel das estratégias de prompt
    - Estratégias padrão disponíveis
    - Criação de estratégias personalizadas
    - Integração com o ComponentConfigurator
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 5: ESTRATÉGIAS DE PROMPT")
    print("=" * 80)

    print("\n5.1: O Papel das Estratégias de Prompt")
    print("-" * 40)

    # Explicação sobre o papel das estratégias
    print("""
As estratégias de prompt são responsáveis por:
- Determinar COMO o prompt será gerado para um cenário específico
- Selecionar quais templates e fragmentos serão usados
- Coordenar a coleta de informações relevantes
- Formatar as mensagens para o LLM

Essencialmente, as estratégias são o "cérebro" que coordena os outros componentes 
do sistema de prompts para criar mensagens adaptadas a diferentes necessidades.
""")

    print("\n5.2: Estratégias Padrão Disponíveis")
    print("-" * 40)

    print("""
O sistema vem com várias estratégias pré-configuradas:

1. StandardStrategy (DEFAULT)
   - Gera UMA ação de teste específica
   - Foco em cobertura eficiente da aplicação
   - Usa o template standard_modular.xml
   - Ideal para exploração passo-a-passo

2. BatchActionStrategy (BATCH_ACTION)
   - Gera MÚLTIPLAS ações de teste em sequência
   - Foco em cenários complexos e fluxos de trabalho
   - Usa o template batch_action_modular.xml
   - Ideal para testes de funcionalidades completas

3. Estratégias especializadas (como Teste001Strategy)
   - Focadas em casos de uso ou requisitos específicos
   - Podem usar templates personalizados
   - Implementam lógica específica para cenários especiais
""")

    print("\n5.3: Criação de Estratégias Personalizadas")
    print("-" * 40)

    # Implementação de uma estratégia personalizada
    class CustomExplorationStrategy(PromptStrategy):
        """Estratégia personalizada para exploração focada em acessibilidade."""

        def __init__(
                self,
                name: str = "accessibility_exploration",
                information_manager=None,
                template_repository=None
        ):
            super().__init__(name, information_manager, template_repository)

        def generate_prompt(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[
            Dict[str, str]]:
            """Gerar prompt focado em testes de acessibilidade."""
            # Contexto padrão se não fornecido
            if context is None:
                context = {}

            # Acrescentar foco de acessibilidade ao contexto
            context["exploration_focus"] = "accessibility"
            context["additional_guidelines"] = """
DIRETRIZES DE ACESSIBILIDADE:
- Verificar contraste de cores para visibilidade
- Testar com tamanhos de fonte aumentados
- Verificar rótulos adequados para leitores de tela
- Testar navegação exclusiva por teclado/gestos
"""

            # Usar template standard, mas com nosso contexto especializado
            # Na implementação real, você poderia criar um template específico
            template_name = "standard_modular"

            # Coletar informações relevantes para o template usando o information_manager
            template_vars = {}

            # Coletar informações de elementos UI para o template
            if self.information_manager:
                ui_elements = self.information_manager.get_information("ui_elements", state, context)
                if ui_elements:
                    template_vars["ui_elements"] = ui_elements

                # Coletar outras informações relevantes
                ui_patterns = self.information_manager.get_information("ui_patterns", state, context)
                if ui_patterns:
                    template_vars["ui_patterns"] = ui_patterns

            # Adicionar informações do estado e contexto
            template_vars["activity"] = state.get(StateEntry.ACTIVITY, "unknown")
            template_vars["package_name"] = state.get(StateEntry.PACKAGE_NAME, "unknown")
            template_vars.update(context)

            # Gerar mensagens usando o template repository
            if self.template_repository:
                try:
                    messages = self.template_repository.create_messages(template_name, template_vars)
                    return messages
                except Exception as e:
                    print(f"Erro ao criar mensagens: {e}")
                    return []

            return []

    # Demonstração da estratégia personalizada
    print("Demonstração de estratégia personalizada:")
    print("""
```python
class CustomExplorationStrategy(PromptStrategy):
    def __init__(self, name="accessibility_exploration", ...):
        super().__init__(name, information_manager, template_repository)
    
    def generate_prompt(self, state, context=None):
        # Modificar contexto para foco em acessibilidade
        context = context or {}
        context["exploration_focus"] = "accessibility"
        context["additional_guidelines"] = "DIRETRIZES DE ACESSIBILIDADE:..."
        
        # Usar template padrão com nosso contexto especializado
        template_name = "standard_modular"
        
        # Coletar informações relevantes
        template_vars = {}
        if self.information_manager:
            ui_elements = self.information_manager.get_information("ui_elements", state, context)
            ...
        
        # Gerar mensagens usando o template repository
        if self.template_repository:
            messages = self.template_repository.create_messages(template_name, template_vars)
            return messages
        
        return []
```

Esta estratégia personalizada:
1. Especializa-se em testes de acessibilidade
2. Adiciona diretrizes específicas ao contexto
3. Reutiliza o template padrão, mas com modificações
4. Coleta informações específicas para seu caso de uso
""")

    print("\n5.4: Registro de Estratégias no ComponentConfigurator")
    print("-" * 40)

    print("""
O registro de estratégias agora é integrado ao ComponentConfigurator:

```python
# Inicialização e configuração
configurator = ComponentConfigurator()
framework = PromptFramework.create(configurator)

# Criar estratégia personalizada
accessibility_strategy = CustomExplorationStrategy(
    information_manager=framework.information_manager,
    template_repository=framework.template_repository
)

# Registrar através do framework (que delega ao ComponentConfigurator)
framework.register_strategy(accessibility_strategy)

# OU registrar diretamente no configurator
configurator.register_strategy(
    "accessibility_exploration", 
    implementation=accessibility_strategy
)

# Registrar estratégia para carregamento preguiçoso (lazy loading)
configurator._registries['strategy'].register_lazy(
    "custom_strategy",
    'my_module.strategies.custom',
    'CustomStrategy'
)

# Usar a estratégia
configurator.set_strategy("accessibility_exploration")
messages = framework.generate_prompt(state, context)
```

Benefícios da integração com ComponentConfigurator:
- Registro centralizado de estratégias
- Evita duplicação de registro e inconsistências
- Suporte para carregamento preguiçoso (lazy loading)
- Persistência de configurações entre sessões
""")

    print("\n5.5: Fluxo de Seleção de Estratégias")
    print("-" * 40)

    # Diagrama do fluxo de seleção de estratégias
    print("""
O fluxo completo de seleção e uso de estratégias:

1. Inicialização
   - Estratégias padrão são registradas no ComponentConfigurator
   - StrategyRegistry atua como proxy para o ComponentConfigurator
   - Estratégias personalizadas podem ser registradas a qualquer momento

2. Configuração
   - A estratégia ativa é definida via ComponentConfigurator
   - configurator.set_strategy("strategy_name")
   - A configuração pode ser salva/carregada de arquivos

3. Geração de Prompt
   - PromptFramework.generate_prompt() é chamado
   - A estratégia configurada é recuperada do StrategyRegistry
   - StrategyRegistry delega ao ComponentConfigurator para obter a estratégia
   - A estratégia é executada com o estado e contexto fornecidos
   - O prompt final é gerado e retornado

4. Fallback
   - Se a estratégia configurada não for encontrada, cai para a estratégia padrão
   - Se nenhuma estratégia estiver disponível, retorna uma lista vazia
""")


###################################################################################
# SEÇÃO 6: CASOS DE USO AVANÇADOS
###################################################################################

def tutorial_section_6():
    """
    Seção 6: Casos de Uso Avançados.
    
    Esta seção demonstra:
    - Uso de análise estática com prompts
    - Coordenação com outros componentes
    - Extensão e personalização avançada
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 6: CASOS DE USO AVANÇADOS")
    print("=" * 80)

    print("\n6.1: Integração com Análise Estática")
    print("-" * 40)

    print("""
O framework de prompts pode ser enriquecido com dados de análise estática:

```python
# Carregar dados de análise estática
static_data = static_analysis_parser.read_static_analysis_files(
    app_folder, apk_filename, package_name
)

# Configurar com dados estáticos
configurator = ComponentConfigurator(static_data)
framework = PromptFramework.create(configurator)

# Criar fragmento que usa dados estáticos
class StaticAnalysisFragment(InformationFragment):
    def generate(self, state, context):
        activity = state.get(StateEntry.ACTIVITY)
        # Acessar dados estáticos do contexto
        if 'static_data' in context:
            static_data = context['static_data']
            # Extrair informações da atividade atual
            activity_info = static_data.get_activity_info(activity)
            return f"ANÁLISE ESTÁTICA:\\n{activity_info}"
        return ""

# Registrar fragmento
framework.register_information_fragment(StaticAnalysisFragment())

# Incluir dados estáticos no contexto
context = {"static_data": static_data}
messages = framework.generate_prompt(state, context)
```

Os dados de análise estática podem enriquecer os prompts com:
- Informações sobre a estrutura da aplicação
- Operações monitoradas disponíveis na atividade atual
- Análise de fluxo de dados e controle
- Informações de alcance e navegação entre telas
""")

    print("\n6.2: Personalização de Templates em Tempo de Execução")
    print("-" * 40)

    print("""
É possível personalizar templates em tempo de execução:

```python
# Criar um template dinâmico
dynamic_template = '''<?xml version="1.0" encoding="UTF-8"?>
<template name="dynamic_template" version="1.0">
  <metadata>
    <description>Template criado dinamicamente</description>
    <created>2025-05-06</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>ui_elements</required>
  </variables>
  <roles>
    <system><![CDATA[
      {% include "system_intro" %}
      
      {{ custom_instructions }}
    ]]></system>
    <user><![CDATA[
      {{ ui_elements }}
    ]]></user>
  </roles>
</template>'''

# Salvar em um arquivo temporário
import tempfile
with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temp:
    temp.write(dynamic_template.encode('utf-8'))
    template_path = temp.name

# Configurar repositório de templates para usar o diretório temporário
temp_dir = os.path.dirname(template_path)
template_repo = Jinja2TemplateRepository(template_dir=temp_dir)

# Usar o template dinâmico
variables = {
    "ui_elements": "...",
    "custom_instructions": "Instruções personalizadas para este teste específico..."
}
messages = template_repo.create_messages("dynamic_template", variables)
```

Este recurso é útil para:
- Testes A/B de diferentes formatos de prompt
- Personalização específica para casos de teste únicos
- Experimentos com novas abordagens de instruções
""")

    print("\n6.3: Integração com Modelos Diferentes")
    print("-" * 40)

    print("""
O framework é flexível para trabalhar com diferentes modelos:

```python
# Configuração para Ollama
configurator.set_llm(
    llm_type="ollama",
    model="llama3",
    base_url="http://localhost:11434"
)

# Configuração para HuggingFace
configurator.set_llm(
    llm_type="huggingface",
    model="meta-llama/Meta-Llama-3.1-8B-Instruct",
    api_key="hf_..."
)

# Configuração para modelo personalizado
class MyCustomLLM:
    def generate(self, messages):
        # Implementação personalizada
        return "Resposta personalizada"

configurator.register_llm("my_custom", implementation=MyCustomLLM)
configurator.set_llm(llm_type="my_custom")
```

O framework é projetado para:
- Funcionar com múltiplos provedores de modelos
- Permitir implementações personalizadas
- Facilitar experimentos comparativos
- Adaptar-se a novos modelos conforme surgem
""")

    print("\n6.4: Orquestração de Testes de Longa Duração")
    print("-" * 40)

    print("""
Para testes mais longos, pode-se implementar uma estratégia de orquestração:

```python
class TestOrchestratorStrategy(PromptStrategy):
    def __init__(self, name="test_orchestrator", ...):
        super().__init__(name, information_manager, template_repository)
        self.test_phase = 0
        self.coverage_data = {}
    
    def generate_prompt(self, state, context=None):
        context = context or {}
        
        # Adaptar com base na fase do teste
        if self.test_phase == 0:
            # Fase inicial: exploração geral
            context["exploration_focus"] = "breadth"
            template_name = "exploration_template"
        elif self.test_phase < 5:
            # Fase intermediária: exploração direcionada
            context["exploration_focus"] = "targeted"
            context["coverage_data"] = self.coverage_data
            template_name = "targeted_template"
        else:
            # Fase final: testes de edge cases
            context["exploration_focus"] = "edge_cases"
            template_name = "edge_case_template"
        
        # Incrementar fase
        self.test_phase += 1
        
        # Renderizar template com base na fase
        template_vars = {...}  # Variáveis para o template
        messages = self.template_repository.create_messages(template_name, template_vars)
        return messages
```

Esta abordagem permite:
- Adaptação da estratégia de teste ao longo do tempo
- Incorporação de feedback de execuções anteriores
- Evolução do foco de teste baseado na cobertura
- Planejamento de longo prazo para testes completos
""")


###################################################################################
# SEÇÃO 7: REFERÊNCIA RÁPIDA
###################################################################################

def tutorial_section_7():
    """
    Seção 7: Referência Rápida.
    
    Esta seção fornece:
    - Código de exemplo para tarefas comuns
    - Lista de componentes principais
    - Dicas e melhores práticas
    """
    print("\n" + "=" * 80)
    print("SEÇÃO 7: REFERÊNCIA RÁPIDA")
    print("=" * 80)

    print("\n7.1: Componentes Principais")
    print("-" * 40)

    print("""
COMPONENTES PRINCIPAIS:

1. PromptFramework:
   - Ponto de entrada principal para geração de prompts
   - Coordena todos os outros componentes
   - Métodos: create(), generate_prompt(), register_strategy(), etc.

2. ComponentConfigurator:
   - Configuração central do sistema
   - Registra e gerencia componentes
   - Métodos: set_llm(), set_strategy(), register_strategy(), etc.

3. Jinja2TemplateRepository:
   - Gerencia templates e fragmentos
   - Carrega e renderiza templates XML com Jinja2
   - Métodos: create_messages(), get_template(), get_fragment(), etc.

4. InformationManager:
   - Gerencia fragmentos de informação
   - Coordena coleta de dados para templates
   - Métodos: register_fragment(), get_information(), etc.

5. ComponentConfigurator (for Strategies):
   - Registra e fornece estratégias de prompt
   - Centraliza a configuração de componentes
   - Métodos: register_strategy(), set_strategy(), create_strategy(), etc.
""")

    print("\n7.2: Código de Exemplo para Tarefas Comuns")
    print("-" * 40)

    print("""
INICIALIZAÇÃO BÁSICA:
```python
configurator = ComponentConfigurator()
framework = PromptFramework.create(configurator)
```

GERAÇÃO DE PROMPT:
```python
state = {
    StateEntry.PACKAGE_NAME: "com.example.app",
    StateEntry.ACTIVITY: "com.example.app.MainActivity",
    "screen_description": "Tela inicial com botões de Login e Registro"
}
messages = framework.generate_prompt(state)
```

CONFIGURAÇÃO DE LLM:
```python
configurator.set_llm(
    llm_type="ollama",
    model="llama3",
    temperature=0.7,
    max_tokens=2000
)
```

SELEÇÃO DE ESTRATÉGIA:
```python
configurator.set_strategy(PromptStrategyType.BATCH_ACTION)
```

CRIAÇÃO DE FRAGMENTO PERSONALIZADO:
```python
class MyFragment(InformationFragment):
    def __init__(self):
        super().__init__("my_fragment", priority=100)
    
    def generate(self, state, context=None):
        return "Conteúdo do meu fragmento"
    
    def should_include(self, state, context=None):
        return True

framework.register_information_fragment(MyFragment())
```

CRIAÇÃO DE ESTRATÉGIA PERSONALIZADA:
```python
class MyStrategy(PromptStrategy):
    def __init__(self):
        super().__init__("my_strategy", information_manager, template_repository)
    
    def generate_prompt(self, state, context=None):
        # Implementação...
        return messages

framework.register_strategy(MyStrategy())
configurator.set_strategy("my_strategy")
```
""")

    print("\n7.3: Dicas e Melhores Práticas")
    print("-" * 40)

    print("""
DICAS E MELHORES PRÁTICAS:

1. Organização:
   - Mantenha templates organizados por domínio ou função
   - Use herança para compartilhar estrutura comum
   - Separe fragmentos em diretórios lógicos

2. Desenvolvimento de Templates:
   - Comece com templates simples e evolua gradualmente
   - Use condicionais para adaptar conteúdo dinamicamente
   - Prefira fragmentos a conteúdo hardcoded para reutilização

3. Fragmentos de Informação:
   - Implemente should_include() criteriosamente para controlar inclusão
   - Use níveis de prioridade para ordenar corretamente
   - Mantenha fragmentos focados em uma responsabilidade

4. Estratégias:
   - Crie estratégias especializadas para casos de uso distintos
   - Reutilize estratégias existentes quando possível
   - Registre estratégias no ComponentConfigurator para integração completa

5. Fluxo de Trabalho de Desenvolvimento:
   - Desenvolva incrementalmente templates, fragmentos e estratégias
   - Teste cada componente isoladamente antes de integrar
   - Monitore o desempenho e ajuste conforme necessário
""")

    print("\n7.4: Solução de Problemas Comuns")
    print("-" * 40)

    print("""
SOLUÇÃO DE PROBLEMAS COMUNS:

1. "Fragmento não encontrado":
   - Verifique o nome exato do fragmento
   - Verifique o caminho/diretório do fragmento
   - Verifique se o fragmento está sendo carregado corretamente

2. "Variável requerida não fornecida":
   - Verifique quais variáveis o template exige
   - Certifique-se de que o estado contém as informações necessárias
   - Verifique se os fragmentos estão gerando corretamente as informações

3. "Estratégia não encontrada":
   - Verifique se a estratégia está registrada corretamente
   - Verifique a ortografia do nome da estratégia
   - Tente registrar novamente a estratégia

4. "Erro ao renderizar template":
   - Verifique a sintaxe Jinja2 no template
   - Verifique se todas as referências a fragmentos estão corretas
   - Verifique se as variáveis têm o formato esperado

5. "Mensagem não gerada":
   - Verifique logs para erros específicos
   - Verifique se todos os componentes estão inicializados
   - Verifique se há exceções na geração do prompt
""")


# Helper to create a fresh framework instance for each demo section
def create_fresh_framework(strategy_type=None):
    """Create a fresh framework instance with clean components to avoid registry conflicts.
    
    This is a simplified version for the tutorial that avoids component registration issues.
    In a real application, you would use PromptFramework.create() directly.
    """
    # Create a fresh configurator
    configurator = ComponentConfigurator()

    # If a strategy type was specified, set it now
    if strategy_type:
        configurator.set_strategy(strategy_type)

    # Create components individually to avoid automatic registration
    info_manager = InformationManager()
    template_repo = Jinja2TemplateRepository()

    # IMPORTANT: For the tutorial, we'll create a simplified framework that doesn't
    # try to auto-register components or handle DroidBotParser
    framework = PromptFramework(
        information_manager=info_manager,
        template_repository=template_repo,
        config=configurator
    )

    # We don't configure the framework to avoid registration of parsers
    # In a real application, you would call framework.configure(configurator)

    return framework, configurator


if __name__ == "__main__":
    # Configure logging with INFO level to reduce noise
    LoggingManager.get_instance().configure_output(console_level=logging.INFO)

    # List of available sections
    sections = [
        "1: Conceitos Básicos",
        "2: Configuração Avançada",
        "3: Sistema de Templates",
        "4: Sistema de Informações e Fragmentos",
        "5: Estratégias de Prompt",
        "6: Casos de Uso Avançados",
        "7: Referência Rápida"
    ]

    print("=" * 80)
    print("TUTORIAL DO FRAMEWORK DE PROMPTS DO RV-ANDROID".center(80))
    print("=" * 80)
    print("\nSeções disponíveis:")
    for i, section in enumerate(sections, 1):
        print(f"  {i}. {section}")

    print("\nPara executar todas as seções, rode o script sem argumentos.")
    print("Para executar uma seção específica, rode com o número da seção como argumento.")
    print("Exemplo: python teste_prompt_framework_02.py 1")

    # Determinar quais seções executar com base nos argumentos
    if len(sys.argv) > 1:
        section_funcs = [
            tutorial_section_1,
            tutorial_section_2,
            tutorial_section_3,
            tutorial_section_4,
            tutorial_section_5,
            tutorial_section_6,
            tutorial_section_7
        ]

        try:
            section_arg = sys.argv[1].strip()
            section_num = int(section_arg)

            if 1 <= section_num <= 7:
                print(f"\nExecutando apenas a seção {section_num}...\n")
                try:
                    section_funcs[section_num - 1]()
                except Exception as e:
                    print(f"Erro ao executar a seção {section_num}: {e}")
            else:
                print(f"Seção inválida: {section_num}. Por favor escolha uma seção de 1 a 7.")
        except ValueError:
            print(f"Argumento inválido: {sys.argv[1]}. Por favor use um número de 1 a 7.")
    else:
        # Executar todas as seções (de forma segura, tratando exceções independentemente)
        try:
            tutorial_section_1()  # Conceitos Básicos
            print("\n" + "=" * 40 + " SEPARAÇÃO ENTRE SEÇÕES " + "=" * 40 + "\n")
        except Exception as e:
            print(f"Erro na seção 1: {e}")
        #
        # try:
        #     tutorial_section_2()  # Configuração Avançada
        #     print("\n" + "=" * 40 + " SEPARAÇÃO ENTRE SEÇÕES " + "=" * 40 + "\n")
        # except Exception as e:
        #     print(f"Erro na seção 2: {e}")
        #
        # try:
        #     tutorial_section_3()  # Sistema de Templates
        #     print("\n" + "=" * 40 + " SEPARAÇÃO ENTRE SEÇÕES " + "=" * 40 + "\n")
        # except Exception as e:
        #     print(f"Erro na seção 3: {e}")
        #
        # try:
        #     tutorial_section_4()  # Sistema de Informações e Fragmentos
        #     print("\n" + "=" * 40 + " SEPARAÇÃO ENTRE SEÇÕES " + "=" * 40 + "\n")
        # except Exception as e:
        #     print(f"Erro na seção 4: {e}")
        
        # As seções seguintes podem ser descomentadas conforme necessário
        # try:
        #     tutorial_section_5()  # Estratégias de Prompt
        #     print("\n" + "=" * 40 + " SEPARAÇÃO ENTRE SEÇÕES " + "=" * 40 + "\n")
        # except Exception as e:
        #     print(f"Erro na seção 5: {e}")

        # try:
        #     tutorial_section_6()  # Casos de Uso Avançados
        #     print("\n" + "=" * 40 + " SEPARAÇÃO ENTRE SEÇÕES " + "=" * 40 + "\n")
        # except Exception as e:
        #     print(f"Erro na seção 6: {e}")

        # try:
        #     tutorial_section_7()  # Referência Rápida
        # except Exception as e:
        #     print(f"Erro na seção 7: {e}")

    print("\n" + "=" * 80)
    print("TUTORIAL CONCLUÍDO".center(80))
    print("=" * 80)
