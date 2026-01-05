#!/usr/bin/env python3
"""
Analyze tool call distribution from screenshots sample.
"""

import base64
import json
import re
from pathlib import Path
from collections import Counter
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from rv_agent.llm.tools import json_parser
from rv_agent.llm.tools.android_tools import create_android_tools

def analyze_sample():
    """Analyze tool call distribution from sample of screenshots."""
    
    print("=" * 80)
    print("📊 ANÁLISE DE DISTRIBUIÇÃO DE TOOLS - Amostragem")
    print("=" * 80)
    print()
    
    # Dataset directory
    dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    
    # Create LLM
    llm = ChatOllama(model="qwen-vision-tools-v2", temperature=0.00001)
    android_tools = create_android_tools()
    llm_with_tools = llm.bind_tools(android_tools)
    
    # Collect all apps
    app_dirs = [d for d in dataset_dir.iterdir() if d.is_dir()]
    app_dirs.sort()
    
    # Sample: 2 screenshots per app (first and middle)
    tool_counter = Counter()
    element_counter = Counter()
    total_analyzed = 0
    
    print(f"📱 Analisando amostra de screenshots (2 por app de {len(app_dirs)} apps)...")
    print()
    
    for app_dir in app_dirs:
        screenshots = sorted(list(app_dir.glob("*.png")))
        if not screenshots:
            continue
        
        # Select 2 screenshots: first and middle
        samples = [screenshots[0]]
        if len(screenshots) > 1:
            samples.append(screenshots[len(screenshots)//2])
        
        for screenshot in samples:
            try:
                # Load image
                with open(screenshot, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                # Create prompt
                prompt = f"""Analyze this Android screen and suggest actions.

IMPORTANT RULES:
- For text input fields (EditText), use android_type_text (NOT android_click)
- For buttons, use android_click
- For lists/scrollable content, use android_swipe
- Provide realistic coordinates based on image dimensions (728x1288)

What actions should be taken?"""
                
                # Send message
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
                    ]
                )
                
                response = llm_with_tools.invoke([message])
                
                # Parse tool calls
                parsed_calls = json_parser.parse_tool_calls_from_text(response.content)
                
                if parsed_calls:
                    for tc in parsed_calls:
                        tool_name = tc['name']
                        tool_counter[tool_name] += 1
                        
                        # Extract element description if available
                        args = tc.get('args', {})
                        elem_desc = args.get('element_description', args.get('description', ''))
                        if elem_desc:
                            # Extract element type from description
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
                
                total_analyzed += 1
                
                if total_analyzed % 10 == 0:
                    print(f"   Progresso: {total_analyzed} screenshots analisados...")
            
            except Exception as e:
                print(f"   ⚠️  Erro em {screenshot.name}: {e}")
                continue
    
    print()
    print("=" * 80)
    print("📊 RESULTADOS DA ANÁLISE")
    print("=" * 80)
    print()
    
    print(f"📷 Total de screenshots analisados: {total_analyzed}")
    print(f"🔧 Total de tool calls extraídas: {sum(tool_counter.values())}")
    print()
    
    # Tool distribution
    print("=" * 80)
    print("🔧 DISTRIBUIÇÃO DE TOOLS")
    print("=" * 80)
    print()
    
    total_tools = sum(tool_counter.values())
    for tool, count in tool_counter.most_common():
        percentage = (count / total_tools * 100) if total_tools > 0 else 0
        print(f"   {tool}: {count} ({percentage:.1f}%)")
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
            print(f"   {elem}: {count} ({percentage:.1f}%)")
    else:
        print("   (Sem dados de elementos - descriptions não disponíveis)")
    print()
    
    # Save results
    results = {
        "total_screenshots": total_analyzed,
        "total_tool_calls": sum(tool_counter.values()),
        "tool_distribution": dict(tool_counter),
        "element_distribution": dict(element_counter)
    }
    
    output_file = Path("tool_distribution_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Resultados salvos em: {output_file}")
    print()

if __name__ == "__main__":
    analyze_sample()
