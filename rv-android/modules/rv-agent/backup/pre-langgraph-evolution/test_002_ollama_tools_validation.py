#!/usr/bin/env python3
"""
RVAgent Test 002: Ollama Tools Validation (Text-Only Models)
Validação de modelos text-only que suportam tools oficialmente

Objetivo: Confirmar como tools funcionam no Ollama:
1. Modelo executa tool automaticamente OU sinaliza para execução manual?
2. Quais modelos realmente suportam tools?
3. Formato de entrada/saída das tools

Modelos a testar (da lista oficial): https://ollama.com/search?c=tools
- llama3.1:8b (disponível)
- qwen3:8b (disponível)
- gemma3:4b (disponível)
- phi4-mini:3.8b (disponível)
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import ollama

# Configuração
RESULTS_DIR = Path("validation_results")
RESULTS_DIR.mkdir(exist_ok=True)

@dataclass
class ToolTestResult:
    """Resultado do teste de tool"""
    model_name: str
    scenario: str
    user_prompt: str
    model_response: str
    tool_calls_detected: bool
    tool_calls_count: int
    tool_calls_data: List[Dict]
    tool_execution_success: bool
    final_response: str
    response_time: float
    error: Optional[str] = None

# Modelos disponíveis que suportam tools
AVAILABLE_MODELS = [
    "llama3.1:8b",      # Meta, excelente suporte
    "qwen3:8b",         # Alibaba, forte suporte
    "gemma3:4b",        # Google, disponível
    "phi4-mini:3.8b"    # Microsoft, leve
]

# Cenários de teste para tools
TEST_SCENARIOS = {
    "simple_math": {
        "description": "Teste simples de calculadora",
        "user_prompt": "Calcule 15 + 27 e me diga o resultado",
        "expected_tool": "calculator",
        "should_call_tool": True
    },

    "weather_query": {
        "description": "Consulta meteorológica",
        "user_prompt": "Qual a temperatura atual em São Paulo?",
        "expected_tool": "get_weather",
        "should_call_tool": True
    },

    "web_search": {
        "description": "Busca na web",
        "user_prompt": "Pesquise informações sobre Ollama tools",
        "expected_tool": "web_search",
        "should_call_tool": True
    },

    "no_tool_needed": {
        "description": "Resposta direta sem tools",
        "user_prompt": "Explique o que é inteligência artificial",
        "expected_tool": None,
        "should_call_tool": False
    },

    "multi_step": {
        "description": "Múltiplas operações",
        "user_prompt": "Calcule 10 * 5, depois some 15 e me diga se está quente em Brasília hoje",
        "expected_tool": ["calculator", "get_weather"],
        "should_call_tool": True
    }
}

# Definição das tools disponíveis
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Realiza cálculos matemáticos básicos",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expressão matemática para calcular (ex: '15 + 27')"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Obtém informações meteorológicas atuais",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nome da cidade"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Unidade de temperatura",
                        "default": "celsius"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca informações na web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["general", "news", "tech", "science"],
                        "description": "Categoria da busca",
                        "default": "general"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_tool_function(tool_name: str, arguments: Dict) -> str:
    """
    Executa a tool real (simulada)

    IMPORTANTE: Esta função demonstra que DEVEMOS EXECUTAR AS TOOLS MANUALMENTE
    O modelo apenas sinaliza qual tool chamar e com quais argumentos
    """
    try:
        if tool_name == "calculator":
            expression = arguments.get("expression", "")
            # Simulação - em produção usar biblioteca de cálculo segura
            result = eval(expression.replace("^", "**"))
            return f"Resultado: {result}"

        elif tool_name == "get_weather":
            city = arguments.get("city", "")
            unit = arguments.get("unit", "celsius")
            # Simulação - em produção usar API meteorológica real
            weather_data = {
                "são paulo": {"temp": 25, "condition": "ensolarado"},
                "brasília": {"temp": 32, "condition": "quente"},
                "rio de janeiro": {"temp": 28, "condition": "parcialmente nublado"}
            }
            city_data = weather_data.get(city.lower(), {"temp": 22, "condition": "dados indisponíveis"})
            temp_symbol = "°C" if unit == "celsius" else "°F"
            if unit == "fahrenheit":
                city_data["temp"] = (city_data["temp"] * 9/5) + 32
            return f"Clima em {city}: {city_data['temp']}{temp_symbol}, {city_data['condition']}"

        elif tool_name == "web_search":
            query = arguments.get("query", "")
            category = arguments.get("category", "general")
            # Simulação - em produção usar API de busca real
            search_results = {
                "ollama": "Ollama é uma ferramenta para executar LLMs localmente. Suporta diversos modelos.",
                "tools": "Tools no Ollama permitem que modelos chamem funções externas para obter dados.",
                "ia": "Inteligência Artificial está revolucionando diversos setores."
            }
            for key, value in search_results.items():
                if key in query.lower():
                    return f"[{category.upper()}] {value}"
            return f"Resultados para '{query}': Informações não encontradas na base simulada"

        else:
            return f"Tool '{tool_name}' não implementada"

    except Exception as e:
        return f"Erro ao executar tool '{tool_name}': {str(e)}"

def test_ollama_tools(model_name: str, scenario: str, scenario_config: Dict) -> ToolTestResult:
    """
    Testa tools com um modelo específico
    """
    print(f"  🔄 Testando {model_name} - {scenario}")

    start_time = time.time()

    try:
        # Primeira chamada: enviar prompt com tools disponíveis
        response = ollama.chat(
            model=model_name,
            messages=[
                {'role': 'user', 'content': scenario_config["user_prompt"]}
            ],
            tools=AVAILABLE_TOOLS
        )

        response_time = time.time() - start_time
        model_response = response['message']['content'] if response['message']['content'] else ""

        # Verificar se há tool_calls
        tool_calls = response['message'].get('tool_calls', [])
        tool_calls_detected = len(tool_calls) > 0

        print(f"    📝 Resposta inicial: {model_response[:100]}...")
        print(f"    🔧 Tool calls detectadas: {len(tool_calls)}")

        # Se há tool calls, executar manualmente e continuar conversa
        final_response = model_response
        tool_execution_success = False

        if tool_calls:
            messages = [
                {'role': 'user', 'content': scenario_config["user_prompt"]},
                {'role': 'assistant', 'content': model_response, 'tool_calls': tool_calls}
            ]

            for tool_call in tool_calls:
                tool_name = tool_call['function']['name']
                arguments = tool_call['function']['arguments']

                print(f"    ⚙️ Executando tool: {tool_name} com args: {arguments}")

                # EXECUTAR TOOL MANUALMENTE (isto é que devemos fazer!)
                tool_result = execute_tool_function(tool_name, arguments)
                tool_execution_success = True

                print(f"    ✅ Resultado da tool: {tool_result}")

                # Adicionar resultado da tool à conversa
                messages.append({
                    'role': 'tool',
                    'content': tool_result,
                    'name': tool_name
                })

            # Segunda chamada: modelo processa resultados das tools
            final_call_response = ollama.chat(
                model=model_name,
                messages=messages
            )
            final_response = final_call_response['message']['content']
            print(f"    🎯 Resposta final: {final_response[:100]}...")

        return ToolTestResult(
            model_name=model_name,
            scenario=scenario,
            user_prompt=scenario_config["user_prompt"],
            model_response=model_response,
            tool_calls_detected=tool_calls_detected,
            tool_calls_count=len(tool_calls),
            tool_calls_data=tool_calls,
            tool_execution_success=tool_execution_success,
            final_response=final_response,
            response_time=response_time
        )

    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return ToolTestResult(
            model_name=model_name,
            scenario=scenario,
            user_prompt=scenario_config["user_prompt"],
            model_response="",
            tool_calls_detected=False,
            tool_calls_count=0,
            tool_calls_data=[],
            tool_execution_success=False,
            final_response="",
            response_time=time.time() - start_time,
            error=str(e)
        )

def run_validation():
    """Executar validação completa"""

    print("🚀 RVAgent Ollama Tools Validation")
    print("="*70)
    print("📋 Objetivo: Confirmar funcionamento de tools em modelos text-only")
    print("🎯 Modelos disponíveis:", ", ".join(AVAILABLE_MODELS))
    print("🧪 Cenários:", ", ".join(TEST_SCENARIOS.keys()))
    print()

    all_results = []

    for model_name in AVAILABLE_MODELS:
        print(f"🔵 Testando modelo: {model_name}")
        print("="*50)

        model_results = []

        for scenario_name, scenario_config in TEST_SCENARIOS.items():
            print(f"\n📝 Cenário: {scenario_name}")
            print(f"   Prompt: {scenario_config['user_prompt']}")

            result = test_ollama_tools(model_name, scenario_name, scenario_config)
            model_results.append(result)
            all_results.append(result)

            # Análise do resultado
            if result.error:
                print(f"    ❌ ERRO: {result.error}")
            else:
                expected = scenario_config["should_call_tool"]
                actual = result.tool_calls_detected
                status = "✅" if expected == actual else "⚠️"
                print(f"    {status} Esperado tool call: {expected}, Detectado: {actual}")
                print(f"    ⏱️ Tempo: {result.response_time:.2f}s")

        # Sumário do modelo
        successful_tests = len([r for r in model_results if not r.error])
        tool_detection_rate = len([r for r in model_results if r.tool_calls_detected]) / len(model_results) * 100

        print(f"\n📊 Sumário {model_name}:")
        print(f"   Testes bem-sucedidos: {successful_tests}/{len(model_results)}")
        print(f"   Taxa de detecção de tools: {tool_detection_rate:.1f}%")
        print("="*50)
        print()

    # Análise comparativa final
    print("\n🏆 ANÁLISE COMPARATIVA FINAL")
    print("="*70)

    for model_name in AVAILABLE_MODELS:
        model_results = [r for r in all_results if r.model_name == model_name]
        success_rate = len([r for r in model_results if not r.error]) / len(model_results) * 100
        tool_rate = len([r for r in model_results if r.tool_calls_detected]) / len(model_results) * 100
        avg_time = sum(r.response_time for r in model_results) / len(model_results)

        print(f"📈 {model_name}:")
        print(f"   ✅ Taxa de sucesso: {success_rate:.1f}%")
        print(f"   🔧 Taxa tool calling: {tool_rate:.1f}%")
        print(f"   ⏱️ Tempo médio: {avg_time:.2f}s")
        print()

    # Salvar resultados detalhados
    results_file = RESULTS_DIR / "ollama_tools_validation_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump([
            {
                "model_name": r.model_name,
                "scenario": r.scenario,
                "user_prompt": r.user_prompt,
                "model_response": r.model_response,
                "tool_calls_detected": r.tool_calls_detected,
                "tool_calls_count": r.tool_calls_count,
                "tool_calls_data": r.tool_calls_data,
                "tool_execution_success": r.tool_execution_success,
                "final_response": r.final_response,
                "response_time": r.response_time,
                "error": r.error
            } for r in all_results
        ], f, indent=2, ensure_ascii=False)

    print(f"💾 Resultados salvos em: {results_file}")

    # Conclusões
    print("\n🎯 CONCLUSÕES PRINCIPAIS:")
    print("="*70)

    working_models = [m for m in AVAILABLE_MODELS
                     if len([r for r in all_results
                            if r.model_name == m and r.tool_calls_detected]) > 0]

    if working_models:
        print(f"✅ Modelos funcionais para tools: {', '.join(working_models)}")
        print("✅ Confirmado: Modelos SINALIZAM tool calls, devemos EXECUTAR manualmente")
        print("✅ Formato: JSON com 'function.name' e 'function.arguments'")
        print("✅ Fluxo: 1) Prompt → 2) Tool calls → 3) Execução manual → 4) Resultado → 5) Resposta final")
    else:
        print("❌ Nenhum modelo funcionou corretamente com tools")

    print("\n🚀 Próximo passo: test_003_ollama_vision_tools.py")

if __name__ == "__main__":
    run_validation()