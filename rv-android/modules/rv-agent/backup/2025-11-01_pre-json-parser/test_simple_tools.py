#!/usr/bin/env python3
"""
Test simples para verificar que qwen-vision-tools-v1 usa tools.
Baseado no script de exemplo do usuário.
"""

from datetime import datetime
from typing import TypedDict, Annotated

from langchain_core.messages import HumanMessage, AnyMessage, SystemMessage
from langchain_ollama import ChatOllama


def dia():
    """
    Retorna a data atual
    :return: a data e hora atuais
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hello_tools():
    llm = ChatOllama(
        model="qwen-vision-tools-v1:latest",
        temperature=0.00001,
        # other params...
    )

    llm_with_tools = llm.bind_tools([dia])
    tool_call = llm_with_tools.invoke([HumanMessage(content="Que dia é hoje?", name="Eu")])
    print(tool_call)


#######################################
print("=" * 80)
print("🧪 TESTE SIMPLES - Tool Calling com qwen-vision-tools-v1")
print("=" * 80)
print()

llm = ChatOllama(
    model="qwen-vision-tools-v1:latest",
    temperature=0.00001,
    # other params...
)

llm_with_tools = llm.bind_tools([dia])
print("📤 Enviando: 'Que dia é hoje?'")
print()

tool_call = llm_with_tools.invoke([HumanMessage(content="Que dia é hoje?", name="Eu")])

print("=" * 80)
print("📥 RESPOSTA:")
print("=" * 80)
print(tool_call)
print()

# Verifica se gerou tool_calls
if hasattr(tool_call, 'tool_calls') and tool_call.tool_calls:
    print("✅ SUCCESS! Tool calls gerados:")
    for tc in tool_call.tool_calls:
        print(f"   - {tc}")
else:
    print("❌ FAILURE! Nenhum tool call gerado")

print("=" * 80)


def main():
    hello_tools()


if __name__ == "__main__":
    main()
