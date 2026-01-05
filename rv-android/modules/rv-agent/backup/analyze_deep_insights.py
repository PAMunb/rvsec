#!/usr/bin/env python3
"""
Deep analysis of JSON parser test results.

Investigates:
1. Elements classified as "Other/Generic" (60%)
2. Coordinate format issues (array vs number)
3. Failed screenshots root causes
4. LLM response patterns
"""

import json
from pathlib import Path
from collections import Counter
import re


def analyze_failures():
    """Analyze the 2 failed screenshots."""

    results_file = Path("test_json_parser_detailed_results.json")

    with open(results_file, 'r') as f:
        stats = json.load(f)

    print("=" * 80)
    print("🔍 ANÁLISE DAS FALHAS (2 screenshots)")
    print("=" * 80)
    print()

    failures = [r for r in stats['detailed_results'] if not r.get('success', False)]

    for i, failure in enumerate(failures, 1):
        print(f"Falha #{i}:")
        print(f"   App: {failure.get('app_name', 'unknown')}")
        print(f"   Screenshot: {failure.get('screenshot', 'unknown')}")
        print(f"   Método: {failure.get('method', 'unknown')}")
        print()
        print(f"   LLM Response:")
        llm_resp = failure.get('llm_response', '')
        print(f"   {llm_resp}")
        print()
        print(f"   DIAGNÓSTICO:")

        # Check for JSON syntax errors
        if '"x":' in llm_resp and '"y":' in llm_resp:
            # Extract arguments section
            args_match = re.search(r'"arguments":\s*\{([^}]+)\}', llm_resp)
            if args_match:
                args_str = args_match.group(1)
                print(f"   Arguments encontrados: {{{args_str}}}")

                # Check for malformed coordinates
                if ', "y":' not in args_str or args_str.count(',') > 3:
                    print(f"   ❌ ERRO: Formato de coordenadas inválido")
                    print(f"      - Esperado: \"x\": NUMBER, \"y\": NUMBER")
                    print(f"      - OU: \"x\": [NUMBER, NUMBER], \"y\": NUMBER")
                else:
                    print(f"   ⚠️  Erro de parsing desconhecido")
        elif '"x":' not in llm_resp or '"y":' not in llm_resp:
            print(f"   ❌ ERRO: Faltam coordenadas x ou y")

        print()
        print("-" * 80)
        print()


def analyze_other_generic_elements():
    """Analyze why 60% of elements are classified as Other/Generic."""

    results_file = Path("test_json_parser_detailed_results.json")

    with open(results_file, 'r') as f:
        stats = json.load(f)

    print("=" * 80)
    print("📱 ANÁLISE DE ELEMENTOS 'Other/Generic' (60.3%)")
    print("=" * 80)
    print()

    # Collect all "Other/Generic" descriptions
    generic_descriptions = []
    for result in stats['detailed_results']:
        for elem in result.get('elements', []):
            if elem.get('type') == 'Other/Generic':
                desc = elem.get('description', '').strip()
                if desc:
                    generic_descriptions.append(desc)

    print(f"Total de elementos 'Other/Generic': {len(generic_descriptions)}")
    print()

    # Find most common patterns
    print("🔤 Padrões mais comuns (top 20):")
    desc_counter = Counter(generic_descriptions)
    for desc, count in desc_counter.most_common(20):
        print(f"   {count:3d}x: {desc}")

    print()
    print("-" * 80)
    print()

    # Analyze description characteristics
    print("📊 Análise de características:")
    print()

    # Length analysis
    lengths = [len(d) for d in generic_descriptions]
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    print(f"   Comprimento médio: {avg_length:.1f} caracteres")
    print(f"   Mais curto: {min(lengths)} caracteres")
    print(f"   Mais longo: {max(lengths)} caracteres")
    print()

    # Word analysis
    all_words = set()
    for desc in generic_descriptions:
        words = desc.lower().split()
        all_words.update(words)

    print(f"   Total de palavras únicas: {len(all_words)}")
    print()

    # Check for potential keywords that could improve classification
    keyword_candidates = Counter()
    for desc in generic_descriptions:
        words = desc.lower().split()
        for word in words:
            if len(word) > 3:  # Skip very short words
                keyword_candidates[word] += 1

    print("   Palavras mais frequentes (potenciais keywords):")
    for word, count in keyword_candidates.most_common(15):
        percentage = (count / len(generic_descriptions) * 100)
        print(f"      {word:20s}: {count:3d} ({percentage:5.1f}%)")

    print()
    print("💡 SUGESTÕES PARA MELHORAR CLASSIFICAÇÃO:")
    print()

    # Suggest new classification rules
    suggestions = []

    if keyword_candidates.get('menu', 0) > 5:
        suggestions.append("   - Adicionar 'menu' → Menu")
    if keyword_candidates.get('settings', 0) > 5:
        suggestions.append("   - Adicionar 'settings' → Menu/Settings")
    if keyword_candidates.get('open', 0) > 5:
        suggestions.append("   - Adicionar 'open' → Button (action)")
    if keyword_candidates.get('view', 0) > 5:
        suggestions.append("   - Adicionar 'view' → Button (action)")
    if keyword_candidates.get('select', 0) > 5:
        suggestions.append("   - Adicionar 'select' → Button (action)")
    if keyword_candidates.get('logo', 0) > 5:
        suggestions.append("   - Adicionar 'logo' → Image/Icon")
    if keyword_candidates.get('arrow', 0) > 5:
        suggestions.append("   - Adicionar 'arrow' → Icon/Navigation")

    for suggestion in suggestions:
        print(suggestion)

    if not suggestions:
        print("   (Nenhuma sugestão automática - revisar manualmente)")

    print()


def analyze_coordinate_formats():
    """Analyze coordinate formats (number vs array)."""

    results_file = Path("test_json_parser_detailed_results.json")

    with open(results_file, 'r') as f:
        stats = json.load(f)

    print("=" * 80)
    print("📍 ANÁLISE DE FORMATOS DE COORDENADAS")
    print("=" * 80)
    print()

    # Collect coordinate formats
    x_formats = Counter()
    y_formats = Counter()
    examples = {
        'x_number': [],
        'x_array': [],
        'y_number': [],
        'y_array': [],
    }

    for result in stats['detailed_results']:
        for tc in result.get('tool_calls', []):
            args = tc.get('arguments', {})
            x = args.get('x')
            y = args.get('y')

            if x is not None:
                if isinstance(x, list):
                    x_formats['array'] += 1
                    if len(examples['x_array']) < 5:
                        examples['x_array'].append({
                            'app': result.get('app_name'),
                            'screenshot': result.get('screenshot'),
                            'value': x
                        })
                elif isinstance(x, (int, float)):
                    x_formats['number'] += 1
                    if len(examples['x_number']) < 5:
                        examples['x_number'].append({
                            'app': result.get('app_name'),
                            'screenshot': result.get('screenshot'),
                            'value': x
                        })
                else:
                    x_formats['other'] += 1

            if y is not None:
                if isinstance(y, list):
                    y_formats['array'] += 1
                    if len(examples['y_array']) < 5:
                        examples['y_array'].append({
                            'app': result.get('app_name'),
                            'screenshot': result.get('screenshot'),
                            'value': y
                        })
                elif isinstance(y, (int, float)):
                    y_formats['number'] += 1
                    if len(examples['y_number']) < 5:
                        examples['y_number'].append({
                            'app': result.get('app_name'),
                            'screenshot': result.get('screenshot'),
                            'value': y
                        })
                else:
                    y_formats['other'] += 1

    print("Formatos de coordenada X:")
    total_x = sum(x_formats.values())
    for fmt, count in x_formats.most_common():
        percentage = (count / total_x * 100) if total_x > 0 else 0
        print(f"   {fmt:10s}: {count:4d} ({percentage:5.1f}%)")
    print()

    print("Formatos de coordenada Y:")
    total_y = sum(y_formats.values())
    for fmt, count in y_formats.most_common():
        percentage = (count / total_y * 100) if total_y > 0 else 0
        print(f"   {fmt:10s}: {count:4d} ({percentage:5.1f}%)")
    print()

    # Show examples
    if examples['x_array']:
        print("Exemplos de X como array:")
        for ex in examples['x_array'][:3]:
            print(f"   {ex['app']} / {ex['screenshot']}: x = {ex['value']}")
        print()

    if examples['x_number']:
        print("Exemplos de X como número:")
        for ex in examples['x_number'][:3]:
            print(f"   {ex['app']} / {ex['screenshot']}: x = {ex['value']}")
        print()

    print("💡 INTERPRETAÇÃO:")
    if x_formats.get('array', 0) > 0:
        print(f"   - {x_formats['array']} tool calls usam arrays para X")
        print(f"     Provavelmente representam bounding boxes [x1, x2]")
    if x_formats.get('number', 0) > 0:
        print(f"   - {x_formats['number']} tool calls usam números para X")
        print(f"     Provavelmente representam pontos únicos")
    print()


def analyze_llm_response_patterns():
    """Analyze LLM response patterns."""

    results_file = Path("test_json_parser_detailed_results.json")

    with open(results_file, 'r') as f:
        stats = json.load(f)

    print("=" * 80)
    print("💬 ANÁLISE DE PADRÕES DE RESPOSTA LLM")
    print("=" * 80)
    print()

    # Collect response lengths
    response_lengths = []
    has_addcriterion = 0
    tool_call_counts = Counter()

    for result in stats['detailed_results']:
        llm_resp = result.get('llm_response', '')
        response_lengths.append(len(llm_resp))

        if 'addCriterion' in llm_resp:
            has_addcriterion += 1

        tc_count = result.get('tool_calls_count', 0)
        tool_call_counts[tc_count] += 1

    avg_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0

    print(f"Comprimento médio das respostas: {avg_length:.1f} caracteres")
    print(f"Respostas mais curta: {min(response_lengths)} caracteres")
    print(f"Respostas mais longa: {max(response_lengths)} caracteres")
    print()

    print(f"Respostas contendo 'addCriterion': {has_addcriterion}/{len(stats['detailed_results'])} ({has_addcriterion/len(stats['detailed_results'])*100:.1f}%)")
    print()

    print("Distribuição de tool calls por resposta:")
    for count, freq in sorted(tool_call_counts.items()):
        percentage = (freq / len(stats['detailed_results']) * 100)
        bar = "█" * int(percentage / 2)
        print(f"   {count} tool call(s): {freq:4d} ({percentage:5.1f}%) {bar}")
    print()

    # Sample diverse responses
    print("📝 Amostras de respostas LLM:")
    print()

    # Sample: shortest response
    shortest_idx = response_lengths.index(min(response_lengths))
    shortest = stats['detailed_results'][shortest_idx]
    print(f"Resposta mais curta ({min(response_lengths)} chars):")
    print(f"   App: {shortest.get('app_name')}")
    print(f"   Screenshot: {shortest.get('screenshot')}")
    print(f"   Response: {shortest.get('llm_response', '')}")
    print()

    # Sample: longest response
    longest_idx = response_lengths.index(max(response_lengths))
    longest = stats['detailed_results'][longest_idx]
    print(f"Resposta mais longa ({max(response_lengths)} chars):")
    print(f"   App: {longest.get('app_name')}")
    print(f"   Screenshot: {longest.get('screenshot')}")
    print(f"   Response (primeiros 300 chars): {longest.get('llm_response', '')[:300]}...")
    print()


if __name__ == "__main__":
    print()
    print("🔬 ANÁLISE PROFUNDA DOS RESULTADOS DO JSON PARSER")
    print()

    # 1. Analyze failures
    analyze_failures()

    # 2. Analyze Other/Generic elements
    analyze_other_generic_elements()

    # 3. Analyze coordinate formats
    analyze_coordinate_formats()

    # 4. Analyze LLM response patterns
    analyze_llm_response_patterns()

    print("=" * 80)
    print("✅ Análise profunda completa!")
    print("=" * 80)
