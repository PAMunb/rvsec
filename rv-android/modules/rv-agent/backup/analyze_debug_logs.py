"""
Analyze DEBUG logs to extract patterns and understand root causes.

Extracts and analyzes:
1. LLM response content (📤 markers)
2. MockDevice state changes (🔍 markers)
3. Action type determination (🎯 markers)
4. JSON parser failures (❌ markers)
"""

import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple


def extract_llm_responses(log_content: str) -> List[Dict]:
    """Extract LLM response content from DEBUG logs."""
    responses = []

    # Find all LLM response content blocks
    pattern = r'📤 LLM Response Content \(first 500 chars\):\n(.*?)(?=\n\d{4}-\d{2}-\d{2}|\Z)'
    matches = re.finditer(pattern, log_content, re.DOTALL)

    for match in matches:
        content = match.group(1).strip()
        responses.append({
            'content': content,
            'length': len(content)
        })

    return responses


def extract_mockdevice_state_changes(log_content: str) -> List[Dict]:
    """Extract MockDevice state changes (BEFORE/AFTER pairs)."""
    state_changes = []

    # Find BEFORE/AFTER pairs
    lines = log_content.split('\n')
    i = 0
    while i < len(lines):
        if '🔍 BEFORE graph invocation:' in lines[i]:
            # Extract BEFORE state
            before_actions = None
            j = i + 1
            while j < len(lines) and '🔍 AFTER graph invocation:' not in lines[j]:
                if 'MockDevice.actions_executed:' in lines[j]:
                    before_actions = int(re.search(r'(\d+)', lines[j]).group(1))
                j += 1

            # Extract AFTER state
            after_actions = None
            new_actions = None
            if j < len(lines):
                while j < len(lines) and not lines[j].startswith('20'):
                    if 'MockDevice.actions_executed:' in lines[j]:
                        after_actions = int(re.search(r'(\d+)', lines[j]).group(1))
                    elif 'New actions:' in lines[j]:
                        new_actions = int(re.search(r'(\d+)', lines[j]).group(1))
                    j += 1

            if before_actions is not None and after_actions is not None:
                state_changes.append({
                    'before': before_actions,
                    'after': after_actions,
                    'new': new_actions or (after_actions - before_actions)
                })

            i = j
        else:
            i += 1

    return state_changes


def extract_json_parser_failures(log_content: str) -> List[Dict]:
    """Extract JSON parser failure patterns."""
    failures = []

    # Find parser failure blocks
    lines = log_content.split('\n')
    for i, line in enumerate(lines):
        if '❌ No tool calls found in response' in line:
            # Look back for the response content
            context_lines = []
            j = i - 1
            count = 0
            while j >= 0 and count < 10:
                if 'Parsing tool calls from:' in lines[j]:
                    # Extract the content being parsed
                    content_match = re.search(r'Parsing tool calls from:\s*(.+)', lines[j])
                    if content_match:
                        failures.append({
                            'line': i,
                            'content_preview': content_match.group(1)[:200]
                        })
                    break
                j -= 1
                count += 1

    return failures


def extract_action_type_determination(log_content: str) -> List[Dict]:
    """Extract action type determination patterns."""
    determinations = []

    lines = log_content.split('\n')
    i = 0
    while i < len(lines):
        if '🎯 ACTION_TYPE DETERMINATION:' in lines[i]:
            # Extract determination details
            details = {}
            j = i + 1
            while j < len(lines) and not lines[j].startswith('20'):
                if 'last_action exists:' in lines[j]:
                    details['has_last_action'] = 'True' in lines[j]
                elif 'action_type:' in lines[j] and 'ACTION_TYPE' not in lines[j]:
                    match = re.search(r'action_type:\s*(\w+)', lines[j])
                    if match:
                        details['action_type'] = match.group(1)
                elif 'valid_action:' in lines[j]:
                    details['valid'] = 'True' in lines[j]
                j += 1

            if details:
                determinations.append(details)

            i = j
        else:
            i += 1

    return determinations


def analyze_llm_response_formats(responses: List[Dict]) -> Dict:
    """Analyze LLM response format patterns."""
    formats = {
        'native_tool_call': 0,
        'xml_format': 0,
        'json_format': 0,
        'text_format': 0,
        'malformed': 0
    }

    examples = defaultdict(list)

    for resp in responses:
        content = resp['content']

        # Check for different formats
        if 'tool_calls' in content.lower():
            formats['native_tool_call'] += 1
            examples['native_tool_call'].append(content[:150])
        elif '<tool_call>' in content:
            formats['xml_format'] += 1
            examples['xml_format'].append(content[:150])
        elif '"name":' in content and '"arguments":' in content:
            formats['json_format'] += 1
            examples['json_format'].append(content[:150])
        elif 'addCriterion' in content or 'Action' in content:
            formats['text_format'] += 1
            examples['text_format'].append(content[:150])
        else:
            formats['malformed'] += 1
            examples['malformed'].append(content[:150])

    return {
        'distribution': formats,
        'examples': dict(examples)
    }


def main():
    """Main analysis entry point."""
    print("=" * 80)
    print("🔬 DEBUG LOG ANALYSIS - Pattern Extraction")
    print("=" * 80)

    # Load log file
    log_file = Path("focused_debug_validation.log")

    if not log_file.exists():
        print(f"\n❌ Log file not found: {log_file}")
        return

    print(f"\n📂 Loading log file: {log_file}")
    log_content = log_file.read_text()
    print(f"   Size: {len(log_content):,} bytes ({len(log_content.split())} lines)")

    # 1. Extract LLM responses
    print("\n" + "=" * 80)
    print("📤 LLM RESPONSE CONTENT ANALYSIS")
    print("=" * 80)

    responses = extract_llm_responses(log_content)
    print(f"\n✅ Extracted {len(responses)} LLM responses")

    if responses:
        format_analysis = analyze_llm_response_formats(responses)
        print(f"\n📊 Response Format Distribution:")
        for fmt, count in format_analysis['distribution'].items():
            pct = count / len(responses) * 100 if responses else 0
            print(f"  {fmt:20s}: {count:3d} ({pct:5.1f}%)")

        print(f"\n📝 Example Responses (first 150 chars):")
        for fmt, examples in format_analysis['examples'].items():
            if examples:
                print(f"\n  {fmt}:")
                for i, ex in enumerate(examples[:3], 1):
                    print(f"    {i}. {ex}")

    # 2. Extract MockDevice state changes
    print("\n" + "=" * 80)
    print("🔍 MOCKDEVICE STATE CHANGES ANALYSIS")
    print("=" * 80)

    state_changes = extract_mockdevice_state_changes(log_content)
    print(f"\n✅ Extracted {len(state_changes)} state change events")

    if state_changes:
        # Count iterations with/without new actions
        with_new = sum(1 for sc in state_changes if sc['new'] > 0)
        without_new = len(state_changes) - with_new

        print(f"\n📊 State Change Distribution:")
        print(f"  Iterations WITH new actions:    {with_new:3d} ({with_new/len(state_changes)*100:5.1f}%)")
        print(f"  Iterations WITHOUT new actions: {without_new:3d} ({without_new/len(state_changes)*100:5.1f}%)")

        # Show examples
        print(f"\n📝 Sample State Changes (first 10):")
        for i, sc in enumerate(state_changes[:10], 1):
            status = "✓" if sc['new'] > 0 else "✗"
            print(f"  {i:2d}. {status} Before: {sc['before']}, After: {sc['after']}, New: {sc['new']}")

    # 3. Extract JSON parser failures
    print("\n" + "=" * 80)
    print("❌ JSON PARSER FAILURE ANALYSIS")
    print("=" * 80)

    failures = extract_json_parser_failures(log_content)
    print(f"\n✅ Extracted {len(failures)} parser failure events")

    if failures:
        print(f"\n📝 Sample Parser Failures (first 5):")
        for i, failure in enumerate(failures[:5], 1):
            print(f"  {i}. Line {failure['line']}: {failure['content_preview']}")

    # 4. Extract action type determination
    print("\n" + "=" * 80)
    print("🎯 ACTION TYPE DETERMINATION ANALYSIS")
    print("=" * 80)

    determinations = extract_action_type_determination(log_content)
    print(f"\n✅ Extracted {len(determinations)} action type determinations")

    if determinations:
        # Count by action type
        action_types = Counter(d.get('action_type', 'UNKNOWN') for d in determinations)
        print(f"\n📊 Action Type Distribution:")
        for atype, count in action_types.most_common():
            pct = count / len(determinations) * 100 if determinations else 0
            print(f"  {atype:20s}: {count:3d} ({pct:5.1f}%)")

        # Count with/without last_action
        with_last = sum(1 for d in determinations if d.get('has_last_action'))
        without_last = len(determinations) - with_last
        print(f"\n📊 Last Action Presence:")
        print(f"  With last_action:    {with_last:3d} ({with_last/len(determinations)*100:5.1f}%)")
        print(f"  Without last_action: {without_last:3d} ({without_last/len(determinations)*100:5.1f}%)")

    # Generate summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY OF FINDINGS")
    print("=" * 80)

    print(f"\n1. LLM Response Patterns:")
    print(f"   - Total responses analyzed: {len(responses)}")
    if responses:
        print(f"   - Most common format: {max(format_analysis['distribution'].items(), key=lambda x: x[1])[0]}")

    print(f"\n2. MockDevice State Changes:")
    print(f"   - Total iterations tracked: {len(state_changes)}")
    if state_changes:
        print(f"   - Iterations reaching tools node: {with_new}/{len(state_changes)} ({with_new/len(state_changes)*100:.1f}%)")
        print(f"   - Iterations NOT reaching tools: {without_new}/{len(state_changes)} ({without_new/len(state_changes)*100:.1f}%)")

    print(f"\n3. JSON Parser Failures:")
    print(f"   - Total parser failures: {len(failures)}")

    print(f"\n4. Action Type Determination:")
    print(f"   - Total determinations: {len(determinations)}")
    if determinations:
        most_common_type = action_types.most_common(1)[0] if action_types else ('N/A', 0)
        print(f"   - Most common type: {most_common_type[0]} ({most_common_type[1]} occurrences)")

    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext: Create detailed report with recommendations")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
