from typing import Literal

from langgraph.graph import StateGraph
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


class MyState(TypedDict):
    package: str
    screenshot: str
    description: str
    prompt: str

def screenshot(state: MyState):
    print(f"Screenshot taken for package: {state["package"]}")
    return {"screenshot": "screenshot.png"}

def generate_prompt(state: MyState):
    print(f"Generate prompt for description: {state["screenshot"]}")
    return {"prompt": "prompt"}

def assistant(state: MyState):
    print(f"Testador for prompt: {state["prompt"]}")
    return state

def verificar_andamento_node(state: MyState):
    """Nó que processa o estado"""
    print(f"Verificar andamento da execucao: {state["prompt"]}")
    # Processar e retornar dict (pode atualizar o estado se necessário)
    return {"prompt": state["prompt"]}  # Mantém o estado atual

def verificar_andamento_route(state: MyState) -> Literal["screenshot", "relatorio"]:
    """Função de roteamento que decide o próximo nó"""
    import random
    if random.random() < 0.5:
        return "screenshot"
    return "relatorio"

def relatorio(state: MyState):
    print(f"Relatorio for package: {state["package"]}")
    return state

builder = StateGraph(MyState)
builder.add_node("screenshot", screenshot)
builder.add_node("generate_prompt", generate_prompt)
builder.add_node("assistant", assistant)
builder.add_node("verificar_andamento", verificar_andamento_node)  # Usa a função de nó
builder.add_node("relatorio", relatorio)

# builder.set_entry_point("screenshot")
builder.add_edge(START, "screenshot")
builder.add_edge("screenshot", "generate_prompt")
builder.add_edge("generate_prompt", "assistant")
builder.add_edge("assistant", "verificar_andamento")
builder.add_conditional_edges("verificar_andamento", verificar_andamento_route)  # Usa a função de roteamento
builder.add_edge("relatorio", END)

grafo = builder.compile()

grafo.invoke({"package": "com.example.app"})

