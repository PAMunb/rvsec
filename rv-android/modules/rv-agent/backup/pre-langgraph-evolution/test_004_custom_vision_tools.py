#!/usr/bin/env python3
"""
RVAgent Test 004: Custom Vision+Tools Models (Specialized)
Teste APENAS de modelos customizados feitos especificamente para vision+tools

DESCOBERTA: Modelos oficiais (llama3.2-vision, qwen2.5vl) não suportam tools
HIPÓTESE: Modelos CUSTOMIZADOS da comunidade podem ter implementado vision+tools

MODELOS CUSTOMIZADOS DISPONÍVEIS (NÃO TESTADOS NO TEST_003):
✅ unitythemaker/llama3.2-vision-tools:latest (7.9GB) ← ESPECIALIZADO!
✅ PetrosStav/gemma3-tools:4b (3.3GB)
✅ MrScarySpaceCat/gemma3-tools:4b (3.3GB)
✅ orieg/gemma3-tools:4b (4.0GB)

OBJETIVO: Confirmar se modelos customizados resolvem limitation vision+tools
"""

import json
import time
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import ollama

# Configuração
RESULTS_DIR = Path("validation_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Screenshot para teste
SCREENSHOT_PATH = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

@dataclass
class CustomVisionToolResult:
    model_name: str
    scenario: str
    success: bool
    tool_calls_detected: bool
    tool_calls_count: int
    response_time: float
    vision_detected: bool
    error: Optional[str] = None
    model_response: str = ""

# MODELOS CUSTOMIZADOS DISPONÍVEIS - Confirmados pelo usuário
CUSTOM_MODELS = [
    "unitythemaker/llama3.2-vision-tools:latest",  # ← ESPECIALIZADO vision+tools!
    "PetrosStav/gemma3-tools:4b",                  # ← Gemma3 + tools variant 1
    "MrScarySpaceCat/gemma3-tools:4b"              # ← Gemma3 + tools variant 2
]

# Tool simples para testar
SIMPLE_ANDROID_TOOL = [{
    "type": "function",
    "function": {
        "name": "android_click",
        "description": "Click on Android UI element",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X coordinate"},
                "y": {"type": "number", "description": "Y coordinate"},
                "element": {"type": "string", "description": "Element description"}
            },
            "required": ["x", "y", "element"]
        }
    }
}]

def test_custom_model(model_name: str, scenario: str, prompt: str) -> CustomVisionToolResult:
    """Testa modelo customizado com vision+tools"""

    print(f"  🔄 Testando {model_name} - {scenario}")
    start_time = time.time()

    try:
        # Verificar se screenshot existe
        if not Path(SCREENSHOT_PATH).exists():
            raise FileNotFoundError(f"Screenshot não encontrado: {SCREENSHOT_PATH}")

        # Carregar imagem
        with open(SCREENSHOT_PATH, 'rb') as f:
            image_data = f.read()

        # Teste com imagem + tools
        response = ollama.chat(
            model=model_name,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }],
            tools=SIMPLE_ANDROID_TOOL
        )

        response_time = time.time() - start_time
        model_response = response['message']['content'] if response['message']['content'] else ""

        # Verificar vision (conseguiu ver a imagem?)
        vision_detected = len(model_response) > 10 and any(word in model_response.lower()
                                                          for word in ['button', 'screen', 'app', 'ui', 'element', 'message', 'digest', 'crypto'])

        # Verificar tool calls
        tool_calls = response['message'].get('tool_calls', [])
        tool_calls_detected = len(tool_calls) > 0

        print(f"    📝 Resposta: {model_response[:80]}...")
        print(f"    👁️ Vision detectada: {'✅' if vision_detected else '❌'}")
        print(f"    🔧 Tool calls: {len(tool_calls)} {'✅' if tool_calls_detected else '❌'}")
        print(f"    ⏱️ Tempo: {response_time:.2f}s")

        # Sucesso = vision + tools funcionando
        success = vision_detected and tool_calls_detected

        return CustomVisionToolResult(
            model_name=model_name,
            scenario=scenario,
            success=success,
            tool_calls_detected=tool_calls_detected,
            tool_calls_count=len(tool_calls),
            response_time=response_time,
            vision_detected=vision_detected,
            model_response=model_response
        )

    except Exception as e:
        print(f"    ❌ Erro: {e}")
        return CustomVisionToolResult(
            model_name=model_name,
            scenario=scenario,
            success=False,
            tool_calls_detected=False,
            tool_calls_count=0,
            response_time=time.time() - start_time,
            vision_detected=False,
            error=str(e)
        )

def run_custom_models_validation():
    """Executar validação dos modelos customizados"""

    print("🚀 RVAgent Custom Vision+Tools Models Validation")
    print("="*70)
    print("🎯 OBJETIVO: Testar modelos CUSTOMIZADOS para vision+tools")
    print("❌ Test_003: Modelos oficiais falharam (0% success)")
    print("✅ Hipótese: Modelos customizados podem ter resolvido a limitação")
    print()
    print("🤖 Modelos customizados disponíveis:")
    for model in CUSTOM_MODELS:
        print(f"   📦 {model}")
    print()

    # Cenários de teste
    scenarios = {
        "basic_vision_tools": "Look at this Android app screenshot. Click on the 'MESSAGE DIGEST' button using android_click tool.",
        "element_detection": "Analyze this CryptoApp screenshot and click on any visible button using the android_click tool with exact coordinates.",
        "vision_understanding": "What do you see in this screenshot? Use android_click to interact with the main button."
    }

    all_results = []
    working_models = []

    for model_name in CUSTOM_MODELS:
        print(f"\n🔵 TESTANDO: {model_name}")
        print("="*60)

        model_results = []

        for scenario_name, prompt in scenarios.items():
            print(f"\n📝 Cenário: {scenario_name}")
            print(f"   Prompt: {prompt[:60]}...")

            result = test_custom_model(model_name, scenario_name, prompt)
            model_results.append(result)
            all_results.append(result)

        # Análise do modelo
        successful_tests = len([r for r in model_results if r.success])
        vision_rate = len([r for r in model_results if r.vision_detected]) / len(model_results) * 100
        tools_rate = len([r for r in model_results if r.tool_calls_detected]) / len(model_results) * 100
        avg_time = sum(r.response_time for r in model_results) / len(model_results)

        print(f"\n📊 Sumário {model_name}:")
        print(f"   ✅ Testes bem-sucedidos: {successful_tests}/{len(model_results)}")
        print(f"   👁️ Taxa visão: {vision_rate:.1f}%")
        print(f"   🔧 Taxa tools: {tools_rate:.1f}%")
        print(f"   ⏱️ Tempo médio: {avg_time:.2f}s")

        if successful_tests > 0:
            working_models.append(model_name)
            print(f"   🎯 CANDIDATO VIÁVEL para RVAgent!")

        print("="*60)

    # Análise final
    print(f"\n🏆 RESULTADO FINAL")
    print("="*70)

    if working_models:
        print(f"✅ SUCESSO! {len(working_models)} modelo(s) funcionam com vision+tools:")
        for model in working_models:
            model_results = [r for r in all_results if r.model_name == model]
            success_rate = len([r for r in model_results if r.success]) / len(model_results) * 100
            print(f"   🎯 {model} - {success_rate:.1f}% success")

        print(f"\n🚀 PRÓXIMO PASSO:")
        print(f"   Implementar RVAgent usando: {working_models[0]}")
        print(f"   Architecture: LangChain + {working_models[0]} + ReAct pattern")

    else:
        print("❌ FALHA: Nenhum modelo customizado funciona com vision+tools")
        print("\n💡 ALTERNATIVAS:")
        print("   1. Pipeline approach: vision primeiro, depois tools")
        print("   2. HuggingFace local models")
        print("   3. Anthropic Computer Use API")
        print("   4. OpenAI Vision + function calling")

    # Salvar resultados
    results_file = RESULTS_DIR / "custom_vision_tools_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump([
            {
                "model_name": r.model_name,
                "scenario": r.scenario,
                "success": r.success,
                "tool_calls_detected": r.tool_calls_detected,
                "tool_calls_count": r.tool_calls_count,
                "response_time": r.response_time,
                "vision_detected": r.vision_detected,
                "error": r.error,
                "model_response": r.model_response
            } for r in all_results
        ], f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados salvos: {results_file}")

    # Conclusão estratégica
    print(f"\n🎯 CONCLUSÃO ESTRATÉGICA:")
    print("="*70)

    if working_models:
        print("✅ VISION+TOOLS RESOLVIDO - Usar modelos customizados!")
        print("✅ Implementar test_005_langchain_integration.py")
        print("✅ RVAgent viável com arquitetura original planejada")
    else:
        print("❌ VISION+TOOLS limitation confirmada mesmo em modelos customizados")
        print("💡 Migrar para estratégias alternativas (HuggingFace, APIs cloud)")
        print("🔍 Usar prompt de pesquisa LLM para soluções 2025")

if __name__ == "__main__":
    run_custom_models_validation()