#!/usr/bin/env python3
"""
Analyze detailed JSON parser test results.

Run this AFTER executing test_json_parser_detailed.py
"""

import json
from pathlib import Path
from collections import Counter

def analyze_detailed_results():
    """Analyze detailed results from test."""

    results_file = Path("test_json_parser_detailed_results.json")

    if not results_file.exists():
        print(f"❌ Results file not found: {results_file}")
        print("   Please run test_json_parser_detailed.py first!")
        return

    # Load results
    with open(results_file, 'r') as f:
        stats = json.load(f)

    print("=" * 80)
    print("📊 ANÁLISE DETALHADA DOS RESULTADOS")
    print("=" * 80)
    print()

    # Basic statistics
    print("📈 ESTATÍSTICAS GERAIS:")
    print(f"   Total de apps: {stats['total_apps']}")
    print(f"   Total de screenshots: {stats['total_screenshots']}")
    print(f"   Parsing bem-sucedido: {stats['successful_parses']} ({stats['successful_parses']/stats['total_screenshots']*100:.1f}%)")
    print(f"   Falhas: {stats['failed_parses']} ({stats['failed_parses']/stats['total_screenshots']*100:.1f}%)")
    print(f"   Erros: {stats['errors']} ({stats['errors']/stats['total_screenshots']*100:.1f}%)")
    print()

    # Tool distribution
    print("=" * 80)
    print("🔧 DISTRIBUIÇÃO DE TOOLS")
    print("=" * 80)
    print()

    tool_dist = stats.get('tool_distribution', {})
    total_tools = sum(tool_dist.values())

    if total_tools > 0:
        # Sort by count
        sorted_tools = sorted(tool_dist.items(), key=lambda x: x[1], reverse=True)

        for tool_name, count in sorted_tools:
            percentage = (count / total_tools * 100)
            bar = "█" * int(percentage / 2)
            print(f"   {tool_name:30s}: {count:4d} ({percentage:5.1f}%) {bar}")
        print()
        print(f"   TOTAL: {total_tools} tool calls")
    else:
        print("   (Sem dados de tools)")
    print()

    # Element distribution
    print("=" * 80)
    print("📱 DISTRIBUIÇÃO DE TIPOS DE ELEMENTOS")
    print("=" * 80)
    print()

    elem_dist = stats.get('element_distribution', {})
    total_elements = sum(elem_dist.values())

    if total_elements > 0:
        # Sort by count
        sorted_elements = sorted(elem_dist.items(), key=lambda x: x[1], reverse=True)

        for elem_type, count in sorted_elements:
            percentage = (count / total_elements * 100)
            bar = "█" * int(percentage / 2)
            print(f"   {elem_type:30s}: {count:4d} ({percentage:5.1f}%) {bar}")
        print()
        print(f"   TOTAL: {total_elements} elementos identificados")
    else:
        print("   (Sem dados de elementos)")
    print()

    # Analyze specific patterns
    print("=" * 80)
    print("🔍 ANÁLISE DE PADRÕES")
    print("=" * 80)
    print()

    # Count apps by success rate
    app_success_rates = {}
    detailed_results = stats.get('detailed_results', [])

    for result in detailed_results:
        app_name = result.get('app_name', 'unknown')
        success = result.get('success', False)

        if app_name not in app_success_rates:
            app_success_rates[app_name] = {'total': 0, 'success': 0}

        app_success_rates[app_name]['total'] += 1
        if success:
            app_success_rates[app_name]['success'] += 1

    # Calculate success rates
    app_rates = []
    for app_name, counts in app_success_rates.items():
        rate = (counts['success'] / counts['total'] * 100) if counts['total'] > 0 else 0
        app_rates.append({
            'app': app_name,
            'rate': rate,
            'success': counts['success'],
            'total': counts['total']
        })

    # Sort by rate
    app_rates.sort(key=lambda x: x['rate'], reverse=True)

    print("📱 Top 5 apps com melhor taxa de sucesso:")
    for i, app_data in enumerate(app_rates[:5], 1):
        print(f"   {i}. {app_data['app']}: {app_data['success']}/{app_data['total']} ({app_data['rate']:.1f}%)")
    print()

    print("⚠️  Apps com taxa de sucesso < 100%:")
    for app_data in app_rates:
        if app_data['rate'] < 100.0:
            print(f"   - {app_data['app']}: {app_data['success']}/{app_data['total']} ({app_data['rate']:.1f}%)")
    print()

    # Sample LLM responses
    print("=" * 80)
    print("📝 EXEMPLOS DE RESPOSTAS LLM")
    print("=" * 80)
    print()

    # Show 3 successful examples
    successful_examples = [r for r in detailed_results if r.get('success', False)][:3]

    for i, example in enumerate(successful_examples, 1):
        print(f"Exemplo {i} - {example.get('app_name', 'unknown')} / {example.get('screenshot', 'unknown')}:")
        print(f"   Método: {example.get('method', 'unknown')}")
        print(f"   Tool calls: {example.get('tool_calls_count', 0)}")

        # Show first tool call
        tool_calls = example.get('tool_calls', [])
        if tool_calls:
            tc = tool_calls[0]
            print(f"   Tool: {tc.get('name', 'unknown')}")
            print(f"   Args: {tc.get('arguments', {})}")

        # Show LLM response preview (first 200 chars)
        llm_resp = example.get('llm_response', '')
        if llm_resp:
            preview = llm_resp[:200] + "..." if len(llm_resp) > 200 else llm_resp
            print(f"   LLM Response: {preview}")
        print()

    print("=" * 80)
    print("✅ Análise completa!")
    print(f"   Resultados detalhados disponíveis em: {results_file}")
    print("=" * 80)


if __name__ == "__main__":
    analyze_detailed_results()
