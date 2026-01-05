#!/usr/bin/env python3
"""
Parse existing log to analyze tool distribution.
NO LLM calls - just parse the log!
"""

import re
import json
from collections import Counter
from pathlib import Path

def parse_log():
    """Parse log file to extract tool distribution."""
    
    log_file = Path("test_json_parser_all_apps.log")
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    print("=" * 80)
    print("📊 ANÁLISE DE DISTRIBUIÇÃO DE TOOLS - Parsing Log")
    print("=" * 80)
    print()
    
    tool_counter = Counter()
    element_counter = Counter()
    
    # Read log
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Extract all XML tool calls from log
    # Pattern: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    pattern = r'<tool_call>\s*(\{.+?\})\s*</tool_call>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    print(f"📝 Parsing {len(matches)} tool calls from log...")
    print()
    
    for match in matches:
        try:
            tool_call = json.loads(match)
            tool_name = tool_call.get('name', 'unknown')
            tool_counter[tool_name] += 1
            
            # Extract element info from arguments
            args = tool_call.get('arguments', {})
            elem_desc = args.get('element_description', args.get('description', ''))
            
            if elem_desc:
                elem_desc_lower = elem_desc.lower()
                if 'button' in elem_desc_lower:
                    element_counter['Button'] += 1
                elif 'text' in elem_desc_lower or 'field' in elem_desc_lower or 'input' in elem_desc_lower:
                    element_counter['Text Field/Input'] += 1
                elif 'icon' in elem_desc_lower:
                    element_counter['Icon'] += 1
                elif 'menu' in elem_desc_lower:
                    element_counter['Menu'] += 1
                elif 'list' in elem_desc_lower:
                    element_counter['List'] += 1
                elif 'card' in elem_desc_lower:
                    element_counter['Card'] += 1
                elif 'tab' in elem_desc_lower:
                    element_counter['Tab'] += 1
                elif 'checkbox' in elem_desc_lower:
                    element_counter['Checkbox'] += 1
                elif 'switch' in elem_desc_lower or 'toggle' in elem_desc_lower:
                    element_counter['Switch/Toggle'] += 1
                elif 'image' in elem_desc_lower or 'photo' in elem_desc_lower:
                    element_counter['Image'] += 1
                else:
                    element_counter['Other/Generic'] += 1
        
        except json.JSONDecodeError:
            continue
    
    print("=" * 80)
    print("📊 RESULTADOS DA ANÁLISE")
    print("=" * 80)
    print()
    
    total_tools = sum(tool_counter.values())
    print(f"🔧 Total de tool calls extraídas: {total_tools}")
    print()
    
    # Tool distribution
    print("=" * 80)
    print("🔧 DISTRIBUIÇÃO DE TOOLS")
    print("=" * 80)
    print()
    
    for tool, count in tool_counter.most_common():
        percentage = (count / total_tools * 100) if total_tools > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"   {tool:25s}: {count:4d} ({percentage:5.1f}%) {bar}")
    print()
    
    # Element distribution
    print("=" * 80)
    print("📱 DISTRIBUIÇÃO DE TIPOS DE ELEMENTOS DA TELA")
    print("=" * 80)
    print()
    
    total_elements = sum(element_counter.values())
    if total_elements > 0:
        for elem, count in element_counter.most_common():
            percentage = (count / total_elements * 100) if total_elements > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"   {elem:25s}: {count:4d} ({percentage:5.1f}%) {bar}")
    else:
        print("   (Sem dados de elementos - descriptions não disponíveis)")
    print()
    
    # Save results
    results = {
        "total_tool_calls": total_tools,
        "tool_distribution": dict(tool_counter),
        "element_distribution": dict(element_counter)
    }
    
    output_file = Path("tool_distribution_from_log.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Resultados salvos em: {output_file}")
    print()

if __name__ == "__main__":
    parse_log()
