"""
Prompt V1 - BASELINE (Original Generic Prompt).

Results:
- Token usage: 1685-1776/iter ✅
- Diversity: 0.000 (100% CLICK) ❌
- Grade: F (Failing) ❌
- Stuck: 75% apps ❌
"""


def get_system_prompt() -> str:
    """
    Original generic prompt without action diversity strategy.

    Problems:
    - No guidance on WHEN to use each action
    - No diversity incentive
    - No anti-stuck strategy
    """
    return """You are an Android app exploration agent. Your goal is to:
1. Systematically explore the app by discovering new screens
2. Interact with different UI elements (CLICK, TYPE_TEXT, LONG_CLICK)
3. Use system actions when appropriate (BACK, HOME)
4. Maintain good coverage of app functionality

Respond with a JSON action in this format:
{
  "action_type": "CLICK|TYPE_TEXT|LONG_CLICK|BACK|HOME",
  "target": "element_id_or_description",
  "text": "text_for_TYPE_TEXT_action",
  "explanation": "why_this_action"
}"""
