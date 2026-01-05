#!/usr/bin/env python3
"""
Extrai respostas LLM reais do log para investigação profunda.
"""

import re
from pathlib import Path


def extract_llm_responses_for_app(log_file, app_name, max_examples=3):
    """Extrai respostas LLM para um app específico."""
    print(f"\n📱 {app_name}")
    print("=" * 80)

    responses = []
    current_app = None
    current_iteration = None
    in_response = False
    current_response_lines = []

    with open(log_file, 'r') as f:
        for line in f:
            # Detecta mudança de app
            if "Validating:" in line:
                match = re.search(r'Validating: (.+\.apk)', line)
                if match:
                    current_app = match.group(1).strip()

            # Detecta iteração
            if "ITERATION" in line:
                match = re.search(r'ITERATION (\d+)/(\d+)', line)
                if match:
                    current_iteration = match.group(1)

            # Detecta início de resposta LLM
            if "LLM Response:" in line or "Tool call:" in line:
                if current_app == app_name:
                    in_response = True
                    current_response_lines = [line]
                    continue

            # Coleta linhas da resposta
            if in_response:
                current_response_lines.append(line)

                # Detecta fim da resposta (linha vazia ou próximo log)
                if line.strip() == "" or "INFO" in line and len(current_response_lines) > 5:
                    response_text = ''.join(current_response_lines)
                    responses.append({
                        'iteration': current_iteration,
                        'text': response_text
                    })
                    in_response = False

                    if len(responses) >= max_examples:
                        break

    # Mostra exemplos
    for i, resp in enumerate(responses[:max_examples], 1):
        print(f"\n--- ITERAÇÃO {resp['iteration']} ---")
        print(resp['text'][:500])  # Primeiros 500 chars
        if len(resp['text']) > 500:
            print(f"... ({len(resp['text']) - 500} caracteres omitidos)")
        print()

    return responses


def extract_validation_failures_for_app(log_file, app_name, max_examples=5):
    """Extrai falhas de validação para um app específico."""
    print(f"\n🔍 FALHAS DE VALIDAÇÃO: {app_name}")
    print("=" * 80)

    validations = []
    current_app = None
    current_iteration = None

    with open(log_file, 'r') as f:
        lines = f.readlines()

        for i, line in enumerate(lines):
            # Detecta mudança de app
            if "Validating:" in line:
                match = re.search(r'Validating: (.+\.apk)', line)
                if match:
                    current_app = match.group(1).strip()

            # Detecta iteração
            if "ITERATION" in line:
                match = re.search(r'ITERATION (\d+)/(\d+)', line)
                if match:
                    current_iteration = match.group(1)

            # Detecta validação
            if current_app == app_name and ("✅ Action VALID" in line or "❌ Action INVALID" in line):
                # Pega contexto (3 linhas antes)
                context_start = max(0, i - 3)
                context = ''.join(lines[context_start:i+1])

                validations.append({
                    'iteration': current_iteration,
                    'valid': "✅" in line,
                    'context': context
                })

                if len(validations) >= max_examples:
                    break

    # Mostra exemplos
    for i, val in enumerate(validations[:max_examples], 1):
        status = "VÁLIDA" if val['valid'] else "INVÁLIDA"
        print(f"\n--- ITERAÇÃO {val['iteration']} - {status} ---")
        print(val['context'])
        print()

    return validations


def main():
    """Investiga apps problemáticos."""
    log_file = Path("multiapp_validation_v7.log")

    if not log_file.exists():
        print("❌ Log file não encontrado!")
        return

    print()
    print("🔬 INVESTIGAÇÃO PROFUNDA: RESPOSTAS LLM E VALIDAÇÕES")
    print()

    # Apps com EditText mas sem TYPE_TEXT
    edittext_apps = [
        "cryptoapp.apk",
        "com.alienpants.leafpicrevived_24.apk"
    ]

    # Apps com 0% ações válidas
    zero_valid_apps = [
        "com.akop.bach_120.apk",
        "com.rafapps.simplenotes_7.apk"
    ]

    print("=" * 80)
    print("🧪 PARTE 1: APPS COM EDITTEXT MAS SEM TYPE_TEXT")
    print("=" * 80)

    for app in edittext_apps:
        extract_llm_responses_for_app(log_file, app, max_examples=2)

    print("\n" * 2)
    print("=" * 80)
    print("🧪 PARTE 2: APPS COM 0% AÇÕES VÁLIDAS")
    print("=" * 80)

    for app in zero_valid_apps:
        extract_llm_responses_for_app(log_file, app, max_examples=2)
        extract_validation_failures_for_app(log_file, app, max_examples=3)

    print("\n" * 2)
    print("=" * 80)
    print("✅ Extração completa!")
    print("=" * 80)


if __name__ == "__main__":
    main()
