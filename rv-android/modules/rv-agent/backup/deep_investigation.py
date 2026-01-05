#!/usr/bin/env python3
"""
Investigação profunda dos 3 problemas:
1. Por que TYPE_TEXT funciona no teste JSON mas não no agente real?
2. Análise detalhada de ações UNKNOWN
3. Rastreamento das "22 ações perdidas"
"""

import json
import re
from pathlib import Path
from collections import Counter


def investigate_type_text_difference():
    """Investiga diferença entre teste JSON e validação completa."""
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO 1: DIFERENÇA TYPE_TEXT")
    print("=" * 80)
    print()

    # Carrega resultados dos dois testes
    json_parser_file = Path("test_json_parser_detailed_results.json")

    if json_parser_file.exists():
        with open(json_parser_file, 'r') as f:
            json_test = json.load(f)

        print("📊 Teste JSON Parser (APENAS screenshot):")
        print(f"   Total: {json_test['total_screenshots']} screenshots")
        print(f"   Distribuição de tools:")
        for tool, count in json_test['tool_distribution'].items():
            total = sum(json_test['tool_distribution'].values())
            pct = (count / total * 100) if total > 0 else 0
            print(f"      {tool:25s}: {count:4d} ({pct:5.1f}%)")
        print()

    print("📊 Validação Completa (Agente REAL):")
    print(f"   Total: 444 ações")
    print(f"   TYPE_TEXT: 0 (0%)")
    print(f"   CLICK: 391 (88.1%)")
    print(f"   SWIPE: 0 (0%)")  # Também desapareceu!
    print()

    print("💡 HIPÓTESE:")
    print("   O contexto COMPLETO do agente está INTERFERINDO na geração de tools!")
    print()
    print("   Diferenças entre os dois testes:")
    print("   - JSON Parser: Prompt SIMPLES (só screenshot)")
    print("   - Agente Real: Prompt COMPLEXO (screenshot + XML dump + screen_description")
    print("                  + histórico + exploration_summary + memory_insights)")
    print()
    print("   Possível causa:")
    print("   1. Screen description não menciona EditText explicitamente")
    print("   2. Histórico de ações (só CLICKs) está viciando a LLM")
    print("   3. Prompt muito longo → LLM se perde e repete padrões")
    print("   4. Ordem das informações no prompt está errada")
    print()


def investigate_unknown_actions():
    """Analisa ações UNKNOWN profundamente."""
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO 2: AÇÕES UNKNOWN")
    print("=" * 80)
    print()

    log_file = Path("multiapp_validation_v7.log")

    if not log_file.exists():
        print("❌ Log não encontrado!")
        return

    # Procura por tool execution logs
    unknown_patterns = []
    current_app = None
    current_iteration = None

    with open(log_file, 'r') as f:
        lines = f.readlines()

        for i, line in enumerate(lines):
            # Detecta app
            if "Validating:" in line:
                match = re.search(r'Validating: (.+\.apk)', line)
                if match:
                    current_app = match.group(1).strip()

            # Detecta iteração
            if "ITERATION" in line:
                match = re.search(r'ITERATION (\d+)/(\d+)', line)
                if match:
                    current_iteration = match.group(1)

            # Procura por execução de tools
            if "Executing tool calls" in line or "Executing" in line and "tool" in line:
                # Pega próximas 10 linhas
                context = ''.join(lines[i:i+10])

                # Verifica se tem informação sobre o tipo de ação
                if "action_type" in context or "Tool call" in context:
                    unknown_patterns.append({
                        'app': current_app,
                        'iteration': current_iteration,
                        'context': context
                    })

    print(f"📊 Encontrados {len(unknown_patterns)} padrões de execução de tools")
    print()

    if unknown_patterns:
        print("📋 Exemplos de execução de tools:")
        for i, pattern in enumerate(unknown_patterns[:3], 1):
            print(f"\nEXEMPLO {i}:")
            print(f"   App: {pattern['app']}, Iteração: {pattern['iteration']}")
            print(pattern['context'][:300])
            print()


def investigate_missing_actions():
    """Investiga as "22 ações perdidas" do cryptoapp."""
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO 3: 22 AÇÕES 'PERDIDAS' (cryptoapp)")
    print("=" * 80)
    print()

    # Carrega JSON do cryptoapp
    cryptoapp_file = Path("validation_results/cryptoapp_validation.json")

    if cryptoapp_file.exists():
        with open(cryptoapp_file, 'r') as f:
            crypto_data = json.load(f)

        print("📊 DADOS DO CRYPTOAPP:")
        print()
        print("A. Métricas 'actions' (do MetricsCollector):")
        print(f"   Total de ações: {sum(crypto_data['actions']['by_type'].values())}")
        for action_type, count in crypto_data['actions']['by_type'].items():
            print(f"      {action_type}: {count}")
        print(f"   Válidas: {crypto_data['actions']['valid']}")
        print(f"   Inválidas: {crypto_data['actions']['invalid']}")
        print()

        print("B. Métricas 'device_actions' (do MockDevice):")
        print(f"   Total de ações: {crypto_data['device_actions']['total_actions']}")
        for action_type, count in crypto_data['device_actions']['action_types'].items():
            print(f"      {action_type}: {count}")
        print(f"   Válidas: {crypto_data['device_actions']['valid_actions']}")
        print(f"   Inválidas: {crypto_data['device_actions']['invalid_actions']}")
        print()

        # Mostra as 3 ações que CHEGARAM ao MockDevice
        print("C. Ações que CHEGARAM ao MockDevice:")
        for i, action in enumerate(crypto_data['device_actions']['actions'], 1):
            print(f"   {i}. Step {action['step']}: {action['action_type']}")
            print(f"      Elemento: {action['element'][:80]}...")
            print(f"      Válida: {action['valid']}")
            print(f"      Razão: {action['reason']}")
            print()

        print("💡 ANÁLISE:")
        total_actions = sum(crypto_data['actions']['by_type'].values())
        device_actions = crypto_data['device_actions']['total_actions']
        diff = total_actions - device_actions

        print(f"   Total de ações geradas pela LLM: {total_actions}")
        print(f"   Ações que chegaram ao MockDevice: {device_actions}")
        print(f"   DIFERENÇA: {diff} ações 'perdidas'")
        print()

        if diff > 0:
            print("   ⚠️  POSSÍVEIS CAUSAS:")
            print("   1. MetricsCollector conta TODAS as iterações (25)")
            print("      Mas MockDevice só recebe ações quando parsing é BEM-SUCEDIDO")
            print()
            print("   2. Se parsing falha → action_type='UNKNOWN'")
            print("      UNKNOWN não é enviado ao MockDevice")
            print()
            print("   3. As 3 ações UNKNOWN do cryptoapp:")
            unknown_count = crypto_data['actions']['by_type'].get('UNKNOWN', 0)
            print(f"      UNKNOWN: {unknown_count}")
            print()
            print("   4. Então:")
            print(f"      22 CLICKs parseados + 3 UNKNOWN = 25 iterações")
            print(f"      Mas apenas 3 CLICKs chegaram ao MockDevice!")
            print()
            print("   ⚠️  HIPÓTESE CRÍTICA:")
            print("      As 22 ações parseadas como CLICK foram DESCARTADAS")
            print("      antes de chegar ao MockDevice!")
            print()
            print("      Possíveis filtros:")
            print("      a) Deduplicação de ações")
            print("      b) Filtro por coordenadas inválidas")
            print("      c) Filtro por elementos não-clicáveis")
            print("      d) Bug no código que envia ações ao MockDevice")

    else:
        print("❌ Arquivo cryptoapp_validation.json não encontrado!")


def extract_llm_responses_unknown_apps():
    """Extrai respostas LLM brutas dos apps com 100% UNKNOWN."""
    print("\n\n")
    print("=" * 80)
    print("🔬 INVESTIGAÇÃO 4: RESPOSTAS LLM DOS APPS COM 100% UNKNOWN")
    print("=" * 80)
    print()

    log_file = Path("multiapp_validation_v7.log")

    if not log_file.exists():
        print("❌ Log não encontrado!")
        return

    target_apps = [
        "com.rafapps.simplenotes_7.apk",
        "com.akop.bach_120.apk"
    ]

    for app_name in target_apps:
        print(f"\n📱 {app_name}")
        print("-" * 80)

        # Procura mensagens da LLM para este app
        in_app = False
        llm_responses = []

        with open(log_file, 'r') as f:
            lines = f.readlines()

            for i, line in enumerate(lines):
                # Detecta início do app
                if "Validating:" in line and app_name in line:
                    in_app = True
                    continue

                # Detecta fim do app
                if in_app and "Validating:" in line and app_name not in line:
                    break

                # Captura respostas LLM
                if in_app and ("LLM Response:" in line or "Tool call:" in line or "Executing" in line):
                    # Pega contexto (próximas 20 linhas)
                    context = ''.join(lines[i:i+20])
                    llm_responses.append(context)

                    if len(llm_responses) >= 2:  # Apenas 2 exemplos
                        break

        if llm_responses:
            for i, resp in enumerate(llm_responses, 1):
                print(f"\n🔍 Resposta LLM #{i}:")
                print(resp[:500])
                if len(resp) > 500:
                    print(f"... ({len(resp) - 500} caracteres omitidos)")
                print()
        else:
            print("   ⚠️  Nenhuma resposta LLM encontrada para este app")

        print("-" * 80)


def main():
    """Executa todas as investigações."""
    print()
    print("🔬 INVESTIGAÇÃO PROFUNDA - 3 PROBLEMAS CRÍTICOS")
    print()

    investigate_type_text_difference()
    investigate_unknown_actions()
    investigate_missing_actions()
    extract_llm_responses_unknown_apps()

    print("\n\n")
    print("=" * 80)
    print("✅ Investigação profunda completa!")
    print("=" * 80)
    print()
    print("📁 Próximos passos:")
    print("   1. Verificar código que envia ações ao MockDevice")
    print("   2. Adicionar logging detalhado no fluxo de ações")
    print("   3. Comparar prompts: JSON Parser vs Agente Real")
    print("   4. Testar com prompt simplificado (sem histórico)")
    print()


if __name__ == "__main__":
    main()
