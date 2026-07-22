#!/usr/bin/env python3
"""
RVAgent Test 005: LangChain Integration with Working Vision+Tools Model
Teste de integração LangChain + PetrosStav/gemma3-tools:4b (66.7% success confirmado)

DESCOBERTA DO TEST_004:
✅ PetrosStav/gemma3-tools:4b: 66.7% success com vision+tools
✅ VISION+TOOLS limitation RESOLVIDA com modelos customizados
✅ RVAgent viável com arquitetura original

OBJETIVO DESTE TESTE:
Implementar arquitetura completa LangChain + ReAct + Tools com modelo working
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Configuração
RESULTS_DIR = Path("validation_results")
RESULTS_DIR.mkdir(exist_ok=True)
SCREENSHOT_PATH = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

# MODELOS CUSTOMIZADOS PARA TESTAR
MODELS_TO_TEST = [
    "PetrosStav/gemma3-tools:4b",                  # 66.7% success confirmado
    "unitythemaker/llama3.2-vision-tools:latest", # Especializado vision+tools
    "MrScarySpaceCat/gemma3-tools:4b"              # Variant gemma3
]

@dataclass
class LangChainTestResult:
    scenario: str
    success: bool
    tool_calls_executed: int
    agent_reasoning: str
    final_response: str
    execution_time: float
    model_name: str = ""
    error: Optional[str] = None

# ============================================
# ANDROID TOOLS PARA LANGCHAIN
# ============================================

@tool
def android_click(x: float, y: float, element_description: str) -> str:
    """
    Click on Android UI element at specific coordinates

    Args:
        x: X coordinate to click
        y: Y coordinate to click
        element_description: Description of element being clicked
    """
    print(f"🤖 TOOL EXECUTED: android_click({x}, {y}) on '{element_description}'")
    # Simulação - em produção chamaria UIAutomator2
    return f"✅ Clicked on '{element_description}' at coordinates ({x}, {y})"

@tool
def android_input(text: str, element_description: str = "") -> str:
    """
    Input text into Android UI element

    Args:
        text: Text to input
        element_description: Description of target element
    """
    print(f"🤖 TOOL EXECUTED: android_input('{text}') on '{element_description}'")
    return f"✅ Inputted '{text}' into {element_description or 'focused element'}"

@tool
def android_back() -> str:
    """Navigate back in Android app"""
    print(f"🤖 TOOL EXECUTED: android_back()")
    return "✅ Pressed back button"

@tool
def android_screenshot_analysis() -> str:
    """Analyze current screenshot for UI elements"""
    print(f"🤖 TOOL EXECUTED: android_screenshot_analysis()")
    # Simulação baseada no CryptoApp
    return """Current screen analysis:
- MESSAGE DIGEST button at (540, 273)
- CIPHER button at (540, 399)
- GENERATED button at (540, 525)
- App title: CryptoApp
- Main menu with 3 cryptography options"""

# ============================================
# LANGCHAIN AGENT SETUP
# ============================================

def create_rvagent_langchain(model_name: str):
    """Criar agent LangChain com tools Android"""

    print(f"🔧 Inicializando LangChain agent com modelo: {model_name}")

    # Configurar LLM
    llm = ChatOllama(
        model=model_name,
        temperature=0.25,  # Phase 0 validated parameters
        top_p=0.8,
        top_k=50
    )

    # Tools disponíveis
    tools = [
        android_click,
        android_input,
        android_back,
        android_screenshot_analysis
    ]

    # Prompt ReAct otimizado para Android testing
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an autonomous Android testing agent using ReAct (Reasoning and Acting) pattern.

GOAL: Test Android applications systematically using available tools.

COORDINATE ENHANCEMENT (Phase 0 validated - 100% vs 30% success):
- Always use explicit coordinates when available from UI descriptions
- Format: android_click(x=540, y=273, element_description="MESSAGE DIGEST button")

TESTING STRATEGY:
1. ANALYZE current screen using android_screenshot_analysis()
2. REASON about what elements to test based on UI analysis
3. ACT by calling appropriate Android tools (android_click, android_input, android_back)

TOOLS AVAILABLE:
- android_click(x, y, element_description): Click UI elements with exact coordinates
- android_input(text, element_description): Input text into fields
- android_back(): Navigate back
- android_screenshot_analysis(): Get current UI analysis

Focus on systematic testing of UI elements with precise coordinates."""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # Criar agent
    agent = create_tool_calling_agent(
        llm=llm.bind_tools(tools),
        tools=tools,
        prompt=prompt
    )

    # Executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
        return_intermediate_steps=True
    )

    return agent_executor

# ============================================
# CENÁRIOS DE TESTE
# ============================================

def test_basic_interaction(agent_executor) -> LangChainTestResult:
    """Teste básico de interação com screenshot"""

    scenario = "basic_interaction"
    print(f"\n📝 CENÁRIO: {scenario}")

    start_time = time.time()

    try:
        # Simular que temos screenshot disponível
        input_prompt = """
        I'm looking at a CryptoApp screenshot.
        First analyze the screen, then click on the MESSAGE DIGEST button.
        Use the tools systematically.
        """

        result = agent_executor.invoke({
            "input": input_prompt
        })

        execution_time = time.time() - start_time

        # Analisar resultado
        tool_calls_executed = len(result.get("intermediate_steps", []))
        final_response = result["output"]

        # Verificar se tools foram usadas corretamente
        success = tool_calls_executed > 0 and "android_click" in str(result)

        print(f"✅ Cenário completado em {execution_time:.2f}s")
        print(f"🔧 Tools executadas: {tool_calls_executed}")

        return LangChainTestResult(
            scenario=scenario,
            success=success,
            tool_calls_executed=tool_calls_executed,
            agent_reasoning=str(result.get("intermediate_steps", [])),
            final_response=final_response,
            execution_time=execution_time
        )

    except Exception as e:
        print(f"❌ Erro: {e}")
        return LangChainTestResult(
            scenario=scenario,
            success=False,
            tool_calls_executed=0,
            agent_reasoning="",
            final_response="",
            execution_time=time.time() - start_time,
            error=str(e)
        )

def test_multi_step_flow(agent_executor) -> LangChainTestResult:
    """Teste de fluxo multi-step com múltiplas tools"""

    scenario = "multi_step_flow"
    print(f"\n📝 CENÁRIO: {scenario}")

    start_time = time.time()

    try:
        input_prompt = """
        Test the CryptoApp systematically:
        1. First analyze the current screen
        2. Click on MESSAGE DIGEST button
        3. Then go back
        4. Click on CIPHER button

        Use tools for each step and provide reasoning.
        """

        result = agent_executor.invoke({
            "input": input_prompt
        })

        execution_time = time.time() - start_time
        tool_calls_executed = len(result.get("intermediate_steps", []))
        final_response = result["output"]

        # Verificar se executou múltiplas tools em sequência
        intermediate_steps = str(result.get("intermediate_steps", []))
        success = (tool_calls_executed >= 3 and
                  "android_screenshot_analysis" in intermediate_steps and
                  "android_click" in intermediate_steps and
                  "android_back" in intermediate_steps)

        print(f"✅ Cenário completado em {execution_time:.2f}s")
        print(f"🔧 Tools executadas: {tool_calls_executed}")

        return LangChainTestResult(
            scenario=scenario,
            success=success,
            tool_calls_executed=tool_calls_executed,
            agent_reasoning=intermediate_steps,
            final_response=final_response,
            execution_time=execution_time
        )

    except Exception as e:
        print(f"❌ Erro: {e}")
        return LangChainTestResult(
            scenario=scenario,
            success=False,
            tool_calls_executed=0,
            agent_reasoning="",
            final_response="",
            execution_time=time.time() - start_time,
            error=str(e)
        )

def test_coordinate_precision(agent_executor) -> LangChainTestResult:
    """Teste de precisão de coordenadas (Phase 0 enhancement)"""

    scenario = "coordinate_precision"
    print(f"\n📝 CENÁRIO: {scenario}")

    start_time = time.time()

    try:
        input_prompt = """
        I need you to click on specific elements in CryptoApp with EXACT coordinates.

        Based on UI analysis, click on:
        1. MESSAGE DIGEST button (should be around x=540, y=273)
        2. CIPHER button (should be around x=540, y=399)

        Use precise coordinates from android_screenshot_analysis first.
        """

        result = agent_executor.invoke({
            "input": input_prompt
        })

        execution_time = time.time() - start_time
        tool_calls_executed = len(result.get("intermediate_steps", []))
        final_response = result["output"]

        # Verificar se usou coordenadas precisas
        intermediate_steps = str(result.get("intermediate_steps", []))
        success = (tool_calls_executed > 0 and
                  ("540" in intermediate_steps or "273" in intermediate_steps or "399" in intermediate_steps))

        print(f"✅ Cenário completado em {execution_time:.2f}s")
        print(f"🔧 Tools executadas: {tool_calls_executed}")
        print(f"📍 Coordenadas precisas: {'✅' if success else '❌'}")

        return LangChainTestResult(
            scenario=scenario,
            success=success,
            tool_calls_executed=tool_calls_executed,
            agent_reasoning=intermediate_steps,
            final_response=final_response,
            execution_time=execution_time
        )

    except Exception as e:
        print(f"❌ Erro: {e}")
        return LangChainTestResult(
            scenario=scenario,
            success=False,
            tool_calls_executed=0,
            agent_reasoning="",
            final_response="",
            execution_time=time.time() - start_time,
            error=str(e)
        )

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================

def run_langchain_integration_test():
    """Executar teste completo de integração LangChain para todos os modelos"""

    print("🚀 RVAgent LangChain Integration Test - Todos os Modelos")
    print("="*70)
    print("🎯 Modelos a testar:")
    for model in MODELS_TO_TEST:
        print(f"   📦 {model}")
    print("✅ Baseado em test_004: Vision+tools funcionando")
    print("🔧 Arquitetura: LangChain + ReAct + Android Tools")
    print()

    all_results = []
    model_summaries = []

    for model_name in MODELS_TO_TEST:
        print(f"\n{'='*70}")
        print(f"🔵 TESTANDO MODELO: {model_name}")
        print("="*70)

        # Criar agent para este modelo
        try:
            agent_executor = create_rvagent_langchain(model_name)
            print("✅ LangChain agent criado com sucesso!")
        except Exception as e:
            print(f"❌ Erro criando agent: {e}")
            continue

        # Executar cenários de teste
        test_scenarios = [
            test_basic_interaction,
            test_multi_step_flow,
            test_coordinate_precision
        ]

        model_results = []

        for test_func in test_scenarios:
            try:
                result = test_func(agent_executor)
                result.model_name = model_name  # Adicionar modelo ao resultado
                model_results.append(result)
                all_results.append(result)
            except Exception as e:
                print(f"❌ Erro no teste: {e}")

        # Análise do modelo
        successful_tests = len([r for r in model_results if r.success])
        total_tools_executed = sum(r.tool_calls_executed for r in model_results)
        avg_time = sum(r.execution_time for r in model_results) / len(model_results) if model_results else 0

        print(f"\n📊 SUMÁRIO {model_name}:")
        print(f"   ✅ Testes bem-sucedidos: {successful_tests}/{len(model_results)}")
        print(f"   🔧 Tools executadas: {total_tools_executed}")
        print(f"   ⏱️ Tempo médio: {avg_time:.2f}s")

        success_rate = successful_tests / len(model_results) * 100 if model_results else 0
        model_summaries.append({
            "model": model_name,
            "success_rate": success_rate,
            "tools_executed": total_tools_executed,
            "avg_time": avg_time
        })

        if successful_tests >= 2:
            print(f"   🎯 MODELO VIÁVEL para RVAgent!")
        else:
            print(f"   ⚠️ Modelo com problemas de integração")

    # Análise comparativa final
    print(f"\n🏆 ANÁLISE COMPARATIVA FINAL")
    print("="*70)

    if model_summaries:
        # Ordenar por success_rate
        model_summaries.sort(key=lambda x: x["success_rate"], reverse=True)

        print("🥇 RANKING DOS MODELOS:")
        for i, summary in enumerate(model_summaries, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
            print(f"{emoji} {summary['model']}")
            print(f"   Success Rate: {summary['success_rate']:.1f}%")
            print(f"   Tools: {summary['tools_executed']}")
            print(f"   Tempo: {summary['avg_time']:.2f}s")
            print()

        # Melhor modelo
        best_model = model_summaries[0]
        if best_model["success_rate"] >= 66:
            print(f"🎉 MODELO CAMPEÃO: {best_model['model']}")
            print(f"✅ Success Rate: {best_model['success_rate']:.1f}%")
            print(f"✅ LangChain + ReAct funcionando perfeitamente")
            print(f"\n🚀 PRÓXIMO PASSO: Implementar RVAgent completo!")
            print(f"   Arquitetura confirmada: LangChain + ReAct + {best_model['model']}")
        else:
            print(f"⚠️ Nenhum modelo atingiu performance satisfatória")
            print(f"💡 Melhor: {best_model['model']} ({best_model['success_rate']:.1f}%)")

    # Salvar resultados
    import json
    results_file = RESULTS_DIR / "langchain_integration_all_models.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "model_summaries": model_summaries,
            "detailed_results": [
                {
                    "model_name": getattr(r, 'model_name', 'unknown'),
                    "scenario": r.scenario,
                    "success": r.success,
                    "tool_calls_executed": r.tool_calls_executed,
                    "agent_reasoning": r.agent_reasoning,
                    "final_response": r.final_response,
                    "execution_time": r.execution_time,
                    "error": r.error
                } for r in all_results
            ]
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados completos salvos: {results_file}")

if __name__ == "__main__":
    run_langchain_integration_test()