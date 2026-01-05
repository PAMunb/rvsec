#!/usr/bin/env python3
"""
Debug: Testar llama3.2-vision suporte a tools
1. Primeiro SEM imagem (só tools)
2. Depois COM imagem (vision + tools)
"""

import ollama
import json

# Tool simples para teste
simple_tool = [{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Realizar cálculo simples",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expressão matemática"
                }
            },
            "required": ["expression"]
        }
    }
}]

def test_model_tools(model_name: str):
    """Testa tools sem imagem"""
    print(f"\n🔵 Testando {model_name} - TOOLS SEM IMAGEM")
    print("-" * 50)

    try:
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': 'Calcule 15 + 27'}],
            tools=simple_tool
        )

        tool_calls = response['message'].get('tool_calls', [])
        print(f"✅ Resposta: {response['message']['content']}")
        print(f"🔧 Tool calls: {len(tool_calls)}")
        if tool_calls:
            print(f"📝 Tool data: {tool_calls[0]['function']}")
            return True
        return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_model_vision_tools(model_name: str):
    """Testa tools COM imagem"""
    print(f"\n🔵 Testando {model_name} - VISION + TOOLS")
    print("-" * 50)

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

    try:
        with open(screenshot_path, 'rb') as f:
            image_data = f.read()

        response = ollama.chat(
            model=model_name,
            messages=[{
                'role': 'user',
                'content': 'What do you see in this image? If there are buttons, calculate how many there are.',
                'images': [image_data]
            }],
            tools=simple_tool
        )

        tool_calls = response['message'].get('tool_calls', [])
        print(f"✅ Resposta: {response['message']['content'][:100]}...")
        print(f"🔧 Tool calls: {len(tool_calls)}")
        if tool_calls:
            print(f"📝 Tool data: {tool_calls[0]['function']}")
            return True
        return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

# Modelos para testar
models_to_test = [
    "llama3.2-vision:latest",
    "llama3.1:8b",  # Controle positivo
    "qwen2.5vl:7b"
]

print("🚀 DEBUG: Vision Models + Tools Support")
print("=" * 60)

for model in models_to_test:
    print(f"\n{'='*60}")
    print(f"📊 MODELO: {model}")
    print("=" * 60)

    # Teste 1: Tools sem imagem
    tools_only = test_model_tools(model)

    # Teste 2: Vision + Tools
    vision_tools = test_model_vision_tools(model)

    # Resumo
    print(f"\n📈 RESUMO {model}:")
    print(f"   🔧 Tools (sem imagem): {'✅' if tools_only else '❌'}")
    print(f"   👁️ Vision + Tools: {'✅' if vision_tools else '❌'}")

    if tools_only and not vision_tools:
        print("   💡 Modelo suporta tools MAS NÃO com imagens!")
    elif tools_only and vision_tools:
        print("   🎯 PERFEITO: Suporta vision + tools!")
    elif not tools_only:
        print("   ❌ Modelo não suporta tools")

print(f"\n🎯 CONCLUSÃO:")
print("="*60)
print("Se algum modelo vision mostrar 'tools SEM imagem = ✅' mas 'vision + tools = ❌'")
print("então o problema é COMBINAR vision + tools no mesmo prompt")
print("Solução: Usar pipeline separado (vision primeiro, depois tools)")