#!/usr/bin/env python3
"""
Análise detalhada dos problemas identificados na validação:

1. TYPE_TEXT não está sendo usado (0% das ações)
2. 4 apps com 0% de ações válidas (todos UNKNOWN)
3. Problemas de parsing de respostas LLM
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict


def load_validation_results():
    """Carrega todos os JSONs de validação."""
    results_dir = Path("validation_results")
    all_results = {}

    for json_file in results_dir.glob("*_validation.json"):
        app_name = json_file.stem.replace("_validation", "")
        with open(json_file, 'r') as f:
            all_results[app_name] = json.load(f)

    return all_results


def analyze_type_text_issue(results):
    """Investiga por que TYPE_TEXT não está sendo usado."""
    print("=" * 80)
    print("🔍 INVESTIGAÇÃO 1: TYPE_TEXT NÃO USADO")
    print("=" * 80)
    print()

    # Apps com EditText
    apps_with_edittext = [
        app for app, data in results.items()
        if 'EditText' in data.get('element_coverage', {}).get('types_seen', [])
    ]

    print(f"📱 Apps com EditText: {len(apps_with_edittext)}")
    for app in apps_with_edittext:
        data = results[app]
        actions = data.get('actions', {})
        print(f"\n   {app}:")
        print(f"      Total de ações: {actions.get('total', 0)}")
        print(f"      TYPE_TEXT: {actions.get('by_type', {}).get('TYPE_TEXT', 0)}")
        print(f"      CLICK: {actions.get('by_type', {}).get('CLICK', 0)}")
        print(f"      UNKNOWN: {actions.get('by_type', {}).get('UNKNOWN', 0)}")

    print("\n" + "=" * 80)
    print("💡 HIPÓTESES:")
    print("=" * 80)
    print()
    print("1. Prompt não está incentivando uso de android_type_text")
    print("2. LLM não está reconhecendo EditText como campo de entrada")
    print("3. Exemplos no prompt não incluem TYPE_TEXT")
    print("4. Screen description não está descrevendo EditText corretamente")
    print()


def analyze_unknown_actions(results):
    """Investiga apps com 100% UNKNOWN."""
    print("=" * 80)
    print("🔍 INVESTIGAÇÃO 2: APPS COM 0% AÇÕES VÁLIDAS (100% UNKNOWN)")
    print("=" * 80)
    print()

    # Encontra apps com 0% de ações válidas
    zero_valid_apps = [
        app for app, data in results.items()
        if data.get('actions', {}).get('valid', 0) == 0
    ]

    print(f"📱 Apps com 0% ações válidas: {len(zero_valid_apps)}")
    print()

    for app in zero_valid_apps:
        data = results[app]
        actions = data.get('actions', {})

        print(f"   {app}:")
        print(f"      Total de ações: {actions.get('total', 0)}")
        print(f"      Ações válidas: {actions.get('valid', 0)}")
        print(f"      Ações inválidas: {actions.get('invalid', 0)}")
        print(f"      Taxa de sucesso: {actions.get('valid_rate', 0) * 100:.1f}%")
        print(f"      Ações por tipo:")
        for action_type, count in actions.get('by_type', {}).items():
            print(f"         {action_type}: {count}")
        print()

    print("=" * 80)
    print("💡 HIPÓTESES:")
    print("=" * 80)
    print()
    print("1. Parsing de respostas LLM falhou para esses apps")
    print("2. Respostas LLM estão em formato inesperado")
    print("3. Nenhum tool call foi extraído corretamente")
    print("4. Validação do MockDevice está muito rigorosa")
    print()


def analyze_log_parsing_errors():
    """Analisa o log para encontrar erros de parsing."""
    print("=" * 80)
    print("🔍 INVESTIGAÇÃO 3: ERROS DE PARSING DE RESPOSTAS LLM")
    print("=" * 80)
    print()

    log_file = Path("multiapp_validation_v7.log")

    if not log_file.exists():
        print("❌ Log file não encontrado!")
        return

    # Padrões para identificar problemas
    parsing_errors = []
    unknown_actions = []
    tool_call_extractions = []

    current_app = None
    current_iteration = None

    with open(log_file, 'r') as f:
        for line in f:
            # Detecta mudança de app
            if "Validating:" in line:
                match = re.search(r'Validating: (.+\.apk)', line)
                if match:
                    current_app = match.group(1)

            # Detecta iteração
            if "ITERATION" in line:
                match = re.search(r'ITERATION (\d+)/(\d+)', line)
                if match:
                    current_iteration = match.group(1)

            # Detecta erros de parsing
            if "Failed to parse" in line or "parsing failed" in line.lower():
                parsing_errors.append({
                    'app': current_app,
                    'iteration': current_iteration,
                    'line': line.strip()
                })

            # Detecta ações UNKNOWN
            if "action_type='UNKNOWN'" in line or "UNKNOWN action" in line:
                unknown_actions.append({
                    'app': current_app,
                    'iteration': current_iteration,
                    'line': line.strip()
                })

            # Detecta tool calls extraídos
            if "Extracted" in line and "tool calls" in line:
                match = re.search(r'Extracted (\d+) tool calls', line)
                if match:
                    tool_call_extractions.append({
                        'app': current_app,
                        'iteration': current_iteration,
                        'count': int(match.group(1))
                    })

    print(f"📊 Estatísticas de Parsing:")
    print(f"   Erros de parsing: {len(parsing_errors)}")
    print(f"   Ações UNKNOWN: {len(unknown_actions)}")
    print(f"   Tool calls extraídos: {len(tool_call_extractions)}")
    print()

    if parsing_errors:
        print("⚠️  Erros de parsing encontrados:")
        for error in parsing_errors[:5]:  # Mostra primeiros 5
            print(f"   App: {error['app']}, Iter: {error['iteration']}")
            print(f"   {error['line'][:100]}...")
        print()

    if unknown_actions:
        print("⚠️  Ações UNKNOWN encontradas:")
        # Conta por app
        unknown_by_app = Counter([a['app'] for a in unknown_actions])
        for app, count in unknown_by_app.most_common(5):
            print(f"   {app}: {count} ações UNKNOWN")
        print()

    # Analisa distribuição de tool calls extraídos
    if tool_call_extractions:
        tool_counts = [tc['count'] for tc in tool_call_extractions]
        print(f"📊 Distribuição de tool calls extraídos:")
        print(f"   Mínimo: {min(tool_counts)}")
        print(f"   Máximo: {max(tool_counts)}")
        print(f"   Média: {sum(tool_counts) / len(tool_counts):.1f}")

        # Conta quantos tiveram 0 tool calls
        zero_calls = sum(1 for c in tool_counts if c == 0)
        print(f"   Iterações com 0 tool calls: {zero_calls} ({zero_calls/len(tool_counts)*100:.1f}%)")
        print()


def find_edittext_examples_in_log():
    """Procura exemplos de telas com EditText no log."""
    print("=" * 80)
    print("🔍 INVESTIGAÇÃO 4: EXEMPLOS DE EDITTEXT NO LOG")
    print("=" * 80)
    print()

    log_file = Path("multiapp_validation_v7.log")

    if not log_file.exists():
        print("❌ Log file não encontrado!")
        return

    # Procura por linhas com EditText
    edittext_contexts = []
    current_app = None
    current_iteration = None
    context_lines = []

    with open(log_file, 'r') as f:
        lines = f.readlines()

        for i, line in enumerate(lines):
            # Detecta mudança de app
            if "Validating:" in line:
                match = re.search(r'Validating: (.+\.apk)', line)
                if match:
                    current_app = match.group(1)

            # Detecta iteração
            if "ITERATION" in line:
                match = re.search(r'ITERATION (\d+)/(\d+)', line)
                if match:
                    current_iteration = match.group(1)

            # Procura EditText
            if "EditText" in line:
                # Pega contexto (5 linhas antes e depois)
                context_start = max(0, i - 5)
                context_end = min(len(lines), i + 6)
                context = ''.join(lines[context_start:context_end])

                edittext_contexts.append({
                    'app': current_app,
                    'iteration': current_iteration,
                    'context': context,
                    'line': line.strip()
                })

    print(f"📱 Encontrados {len(edittext_contexts)} menções a EditText no log")
    print()

    if edittext_contexts:
        # Mostra primeiro exemplo completo
        print("📋 EXEMPLO 1 (contexto completo):")
        print("-" * 80)
        example = edittext_contexts[0]
        print(f"App: {example['app']}, Iteração: {example['iteration']}")
        print()
        print(example['context'])
        print("-" * 80)
        print()

        # Mostra mais 2 exemplos (resumidos)
        if len(edittext_contexts) > 1:
            print("📋 OUTROS EXEMPLOS (resumidos):")
            for i, example in enumerate(edittext_contexts[1:3], 2):
                print(f"\nEXEMPLO {i}:")
                print(f"   App: {example['app']}, Iteração: {example['iteration']}")
                print(f"   Linha: {example['line'][:100]}...")
            print()


def main():
    """Executa todas as análises."""
    print()
    print("🔬 ANÁLISE DETALHADA DOS PROBLEMAS DE VALIDAÇÃO")
    print()

    # Carrega resultados
    print("📂 Carregando resultados de validação...")
    results = load_validation_results()
    print(f"✅ {len(results)} apps carregados")
    print()

    # Análise 1: TYPE_TEXT
    analyze_type_text_issue(results)

    # Análise 2: UNKNOWN actions
    analyze_unknown_actions(results)

    # Análise 3: Parsing errors
    analyze_log_parsing_errors()

    # Análise 4: EditText examples
    find_edittext_examples_in_log()

    print("=" * 80)
    print("✅ Análise completa!")
    print("=" * 80)


if __name__ == "__main__":
    main()
