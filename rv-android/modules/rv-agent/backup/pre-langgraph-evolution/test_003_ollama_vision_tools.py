#!/usr/bin/env python3
"""
RVAgent Test 003: Ollama Vision + Tools Validation
Validação de modelos de visão que também suportam tools

DESCOBERTA DO TEST_002:
✅ llama3.1:8b: 100% sucesso com tools (text-only)
✅ qwen3:8b: 80% sucesso com tools (text-only)
✅ Tools funcionam: modelo sinaliza → aplicação executa → resultado retorna

OBJETIVO DESTE TESTE:
Testar modelos que combinam VISION + TOOLS para o RVAgent final

Modelos de visão disponíveis:
- unitythemaker/llama3.2-vision-tools:latest (7.9GB) ← ESPECIALIZADO!
- llama3.2-vision:latest (7.8GB)
- qwen2.5vl:7b (6.0GB)
- granite3.2-vision:2b (2.4GB)
- llava-llama3:8b (5.5GB)
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import ollama
from PIL import Image

# Configuração
RESULTS_DIR = Path("validation_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Screenshots do CryptoApp para teste
CRYPTOAPP_SCREENSHOTS = [
    "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
]

@dataclass
class VisionToolTestResult:
    """Resultado do teste de vision + tools"""
    model_name: str
    scenario: str
    screenshot_path: str
    user_prompt: str
    model_response: str
    tool_calls_detected: bool
    tool_calls_count: int
    tool_calls_data: List[Dict]
    tool_execution_success: bool
    final_response: str
    response_time: float
    vision_understanding: str  # Como o modelo interpretou a imagem
    coordinate_precision: Optional[Tuple[int, int]] = None  # Se gerou coordenadas
    error: Optional[str] = None

# Modelos de visão disponíveis que PODEM suportar tools
VISION_MODELS_TO_TEST = [
    "unitythemaker/llama3.2-vision-tools:latest",  # Especializado vision+tools
    "llama3.2-vision:latest",    # Meta oficial
    "qwen2.5vl:7b",             # Alibaba, bom histórico
    "granite3.2-vision:2b",     # IBM, pode ter suporte
    "llava-llama3:8b"           # Baseado em llama3
]

# Cenários de teste para vision + tools
VISION_TOOL_SCENARIOS = {
    "android_click_detection": {
        "description": "Detectar elementos clicáveis e gerar coordenadas",
        "user_prompt": "Analyze this Android app screenshot. Identify clickable elements and use the android_click tool to click on the 'MESSAGE DIGEST' button.",
        "expected_tool": "android_click",
        "should_call_tool": True
    },

    "ui_analysis_with_description": {
        "description": "Analisar UI e descrever usando tools",
        "user_prompt": "Look at this CryptoApp screenshot. Use the describe_ui tool to provide detailed analysis of what you see.",
        "expected_tool": "describe_ui",
        "should_call_tool": True
    },

    "coordinate_generation": {
        "description": "Gerar coordenadas precisas para elementos",
        "user_prompt": "In this Android screenshot, find the center coordinates of the MESSAGE DIGEST button and call the get_coordinates tool.",
        "expected_tool": "get_coordinates",
        "should_call_tool": True
    },

    "vision_only_response": {
        "description": "Resposta puramente visual sem tools",
        "user_prompt": "What do you see in this image? Just describe it.",
        "expected_tool": None,
        "should_call_tool": False
    },

    "mixed_analysis": {
        "description": "Análise mista: visão + busca + coordenadas",
        "user_prompt": "Analyze this app screenshot, search for information about cryptography, and provide coordinates for the main button.",
        "expected_tool": ["describe_ui", "web_search", "android_click"],
        "should_call_tool": True
    }
}

# Tools específicas para Android/RVAgent
ANDROID_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "android_click",
            "description": "Click on Android UI elements using coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "X coordinate to click"
                    },
                    "y": {
                        "type": "number",
                        "description": "Y coordinate to click"
                    },
                    "element_description": {
                        "type": "string",
                        "description": "Description of the element being clicked"
                    }
                },
                "required": ["x", "y", "element_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "describe_ui",
            "description": "Provide detailed description of Android UI elements",
            "parameters": {
                "type": "object",
                "properties": {
                    "main_elements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of main UI elements visible"
                    },
                    "app_type": {
                        "type": "string",
                        "description": "Type of application (e.g., 'crypto', 'game', 'utility')"
                    },
                    "interaction_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Suggested next interactions"
                    }
                },
                "required": ["main_elements", "app_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_coordinates",
            "description": "Extract precise coordinates of UI elements",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_name": {
                        "type": "string",
                        "description": "Name of the element to get coordinates for"
                    },
                    "coordinates": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"}
                        },
                        "required": ["x", "y"]
                    }
                },
                "required": ["element_name", "coordinates"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search for information related to the app content",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context from the visual analysis"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_android_tool(tool_name: str, arguments: Dict) -> str:
    """
    Simula execução de tools Android/RVAgent
    """
    try:
        if tool_name == "android_click":
            x = arguments.get("x", 0)
            y = arguments.get("y", 0)
            element = arguments.get("element_description", "unknown")
            return f"✅ Clicked on '{element}' at coordinates ({x}, {y})"

        elif tool_name == "describe_ui":
            elements = arguments.get("main_elements", [])
            app_type = arguments.get("app_type", "unknown")
            suggestions = arguments.get("interaction_suggestions", [])

            result = f"UI Analysis:\n"
            result += f"App Type: {app_type}\n"
            result += f"Main Elements: {', '.join(elements)}\n"
            if suggestions:
                result += f"Suggestions: {', '.join(suggestions)}"
            return result

        elif tool_name == "get_coordinates":
            element_name = arguments.get("element_name", "")
            coords = arguments.get("coordinates", {"x": 0, "y": 0})
            return f"Coordinates for '{element_name}': ({coords['x']}, {coords['y']})"

        elif tool_name == "web_search":
            query = arguments.get("query", "")
            context = arguments.get("context", "")
            # Simulação baseada no CryptoApp
            crypto_info = {
                "cryptography": "Cryptography is the practice of secure communication techniques.",
                "message digest": "Message digest algorithms create fixed-size hash values from input data.",
                "cipher": "Ciphers are algorithms for encryption and decryption of data.",
                "android crypto": "Android provides cryptographic APIs for secure app development."
            }

            for key, value in crypto_info.items():
                if key in query.lower():
                    return f"Search result for '{query}': {value}"
            return f"Search result for '{query}': General cryptography information."

        else:
            return f"Tool '{tool_name}' executed with args: {arguments}"

    except Exception as e:
        return f"Error executing tool '{tool_name}': {str(e)}"

def load_image_as_base64(image_path: str) -> str:
    """Carregar imagem como base64 para o modelo"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def test_vision_tools(model_name: str, scenario: str, scenario_config: Dict, screenshot_path: str) -> VisionToolTestResult:
    """
    Testa vision + tools com um modelo específico
    """
    print(f"  🔄 Testando {model_name} - {scenario}")
    print(f"     📸 Screenshot: {Path(screenshot_path).name}")

    start_time = time.time()

    try:
        # Verificar se screenshot existe
        if not Path(screenshot_path).exists():
            raise FileNotFoundError(f"Screenshot não encontrado: {screenshot_path}")

        # Carregar imagem
        with open(screenshot_path, 'rb') as f:
            image_data = f.read()

        # Primeira chamada: prompt + imagem + tools
        messages = [
            {
                'role': 'user',
                'content': scenario_config["user_prompt"],
                'images': [image_data]  # Ollama aceita bytes diretamente
            }
        ]

        response = ollama.chat(
            model=model_name,
            messages=messages,
            tools=ANDROID_TOOLS
        )

        response_time = time.time() - start_time
        model_response = response['message']['content'] if response['message']['content'] else ""

        # Analisar compreensão visual
        vision_understanding = model_response[:200] + "..." if len(model_response) > 200 else model_response

        # Verificar tool_calls
        tool_calls = response['message'].get('tool_calls', [])
        tool_calls_detected = len(tool_calls) > 0

        print(f"    📝 Resposta inicial: {model_response[:100]}...")
        print(f"    🔧 Tool calls detectadas: {len(tool_calls)}")
        print(f"    👁️ Compreensão visual: {vision_understanding[:50]}...")

        # Extrair coordenadas se presentes
        coordinate_precision = None
        for tool_call in tool_calls:
            if tool_call['function']['name'] in ['android_click', 'get_coordinates']:
                args = tool_call['function']['arguments']
                if 'x' in args and 'y' in args:
                    coordinate_precision = (args['x'], args['y'])
                elif 'coordinates' in args:
                    coords = args['coordinates']
                    coordinate_precision = (coords['x'], coords['y'])

        # Executar tools se detectadas
        final_response = model_response
        tool_execution_success = False

        if tool_calls:
            messages.append({
                'role': 'assistant',
                'content': model_response,
                'tool_calls': tool_calls
            })

            for tool_call in tool_calls:
                tool_name = tool_call['function']['name']
                arguments = tool_call['function']['arguments']

                print(f"    ⚙️ Executando tool: {tool_name} com args: {arguments}")

                # Executar tool
                tool_result = execute_android_tool(tool_name, arguments)
                tool_execution_success = True

                print(f"    ✅ Resultado da tool: {tool_result[:100]}...")

                # Adicionar resultado à conversa
                messages.append({
                    'role': 'tool',
                    'content': tool_result,
                    'name': tool_name
                })

            # Segunda chamada: modelo processa resultados
            final_call_response = ollama.chat(
                model=model_name,
                messages=messages
            )
            final_response = final_call_response['message']['content']
            print(f"    🎯 Resposta final: {final_response[:100]}...")

        return VisionToolTestResult(
            model_name=model_name,
            scenario=scenario,
            screenshot_path=screenshot_path,
            user_prompt=scenario_config["user_prompt"],
            model_response=model_response,
            tool_calls_detected=tool_calls_detected,
            tool_calls_count=len(tool_calls),
            tool_calls_data=tool_calls,
            tool_execution_success=tool_execution_success,
            final_response=final_response,
            response_time=response_time,
            vision_understanding=vision_understanding,
            coordinate_precision=coordinate_precision
        )

    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return VisionToolTestResult(
            model_name=model_name,
            scenario=scenario,
            screenshot_path=screenshot_path,
            user_prompt=scenario_config["user_prompt"],
            model_response="",
            tool_calls_detected=False,
            tool_calls_count=0,
            tool_calls_data=[],
            tool_execution_success=False,
            final_response="",
            response_time=time.time() - start_time,
            vision_understanding="",
            error=str(e)
        )

def run_vision_tools_validation():
    """Executar validação completa de vision + tools"""

    print("🚀 RVAgent Ollama Vision + Tools Validation")
    print("="*70)
    print("📋 Objetivo: Testar modelos que combinam VISION + TOOLS")
    print("🎯 Baseado nas descobertas do test_002:")
    print("   ✅ llama3.1:8b: 100% sucesso tools (text-only)")
    print("   ✅ Confirmado: modelo sinaliza → app executa → resultado retorna")
    print()
    print("🖼️ Screenshots:", [Path(p).name for p in CRYPTOAPP_SCREENSHOTS])
    print("🤖 Modelos:", [m.split('/')[-1] for m in VISION_MODELS_TO_TEST])
    print("🧪 Cenários:", list(VISION_TOOL_SCENARIOS.keys()))
    print()

    all_results = []

    for model_name in VISION_MODELS_TO_TEST:
        print(f"🔵 Testando modelo: {model_name}")
        print("="*60)

        model_results = []

        for screenshot_path in CRYPTOAPP_SCREENSHOTS:
            print(f"\n📸 Screenshot: {Path(screenshot_path).name}")

            for scenario_name, scenario_config in VISION_TOOL_SCENARIOS.items():
                print(f"\n📝 Cenário: {scenario_name}")
                print(f"   Prompt: {scenario_config['user_prompt'][:60]}...")

                result = test_vision_tools(model_name, scenario_name, scenario_config, screenshot_path)
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
                    if result.coordinate_precision:
                        print(f"    📍 Coordenadas: {result.coordinate_precision}")

        # Sumário do modelo
        successful_tests = len([r for r in model_results if not r.error])
        tool_detection_rate = len([r for r in model_results if r.tool_calls_detected]) / len(model_results) * 100
        vision_tests = len([r for r in model_results if r.vision_understanding])
        coords_generated = len([r for r in model_results if r.coordinate_precision])

        print(f"\n📊 Sumário {model_name}:")
        print(f"   ✅ Testes bem-sucedidos: {successful_tests}/{len(model_results)}")
        print(f"   🔧 Taxa de detecção de tools: {tool_detection_rate:.1f}%")
        print(f"   👁️ Testes com visão: {vision_tests}/{len(model_results)}")
        print(f"   📍 Coordenadas geradas: {coords_generated}")
        print("="*60)
        print()

    # Análise comparativa final
    print("\n🏆 ANÁLISE COMPARATIVA FINAL")
    print("="*70)

    working_models = []
    for model_name in VISION_MODELS_TO_TEST:
        model_results = [r for r in all_results if r.model_name == model_name]
        if not model_results:
            continue

        success_rate = len([r for r in model_results if not r.error]) / len(model_results) * 100
        tool_rate = len([r for r in model_results if r.tool_calls_detected]) / len(model_results) * 100
        vision_rate = len([r for r in model_results if r.vision_understanding]) / len(model_results) * 100
        coord_rate = len([r for r in model_results if r.coordinate_precision]) / len(model_results) * 100
        avg_time = sum(r.response_time for r in model_results) / len(model_results)

        print(f"📈 {model_name}:")
        print(f"   ✅ Taxa de sucesso: {success_rate:.1f}%")
        print(f"   🔧 Taxa tool calling: {tool_rate:.1f}%")
        print(f"   👁️ Taxa visão: {vision_rate:.1f}%")
        print(f"   📍 Taxa coordenadas: {coord_rate:.1f}%")
        print(f"   ⏱️ Tempo médio: {avg_time:.2f}s")

        if success_rate > 50 and tool_rate > 50 and vision_rate > 50:
            working_models.append(model_name)
        print()

    # Salvar resultados (corrigir erro de serialização)
    results_file = RESULTS_DIR / "vision_tools_validation_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump([
            {
                "model_name": r.model_name,
                "scenario": r.scenario,
                "screenshot_path": r.screenshot_path,
                "user_prompt": r.user_prompt,
                "model_response": r.model_response,
                "tool_calls_detected": r.tool_calls_detected,
                "tool_calls_count": r.tool_calls_count,
                "tool_calls_data": [
                    {
                        "function": {
                            "name": call['function']['name'],
                            "arguments": call['function']['arguments']
                        }
                    } for call in r.tool_calls_data
                ],  # Serializar manualmente
                "tool_execution_success": r.tool_execution_success,
                "final_response": r.final_response,
                "response_time": r.response_time,
                "vision_understanding": r.vision_understanding,
                "coordinate_precision": r.coordinate_precision,
                "error": r.error
            } for r in all_results
        ], f, indent=2, ensure_ascii=False)

    print(f"💾 Resultados salvos em: {results_file}")

    # Conclusões para RVAgent
    print("\n🎯 CONCLUSÕES PARA RVAGENT:")
    print("="*70)

    if working_models:
        print(f"✅ Modelos viáveis para RVAgent: {len(working_models)}")
        for model in working_models:
            print(f"   🤖 {model}")
        print("✅ Combinação VISION + TOOLS confirmada!")
        print("✅ Próximo passo: test_004_langchain_ollama_agent.py")
    else:
        print("❌ Nenhum modelo combina adequadamente VISION + TOOLS")
        print("💡 Alternativas:")
        print("   1. Usar llama3.1:8b (text-only) + vision separada")
        print("   2. Testar outros modelos vision+tools")
        print("   3. Implementar fallback strategy")

    print("\n🚀 Próximo: Implementar RVAgent com LangChain + melhor modelo encontrado")

if __name__ == "__main__":
    run_vision_tools_validation()