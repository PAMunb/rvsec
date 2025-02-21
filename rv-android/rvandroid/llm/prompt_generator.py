import logging
import os
import sys

from rvandroid.app import App
from rvandroid.parser.static import gator_parser, reach_parser, gesda_parser, static_analysis_parser
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.droidbot.visitor import ScreenDescription


class PromptGenerator:
    def __init__(self, model):
        self.model = model

    def create_context(self, static_data: StaticAnalysisData) -> str:
        context = []

        # Informações sobre a tela atual
        context.append(self._format_current_window(static_data.current_window))

        # Informações sobre métodos alvo
        context.append(self._format_target_methods(static_data.target_methods,
                                                   static_data.method_coverage))

        # Informações sobre transições possíveis
        context.append(self._format_transitions(static_data.wtg,
                                                static_data.current_window))

        return "\n".join(context)

    def _format_current_window(self, window: Window) -> str:
        widgets_info = []
        for widget in window.widgets:
            widget_desc = f"Widget ID: {widget.id}\n"
            widget_desc += f"Type: {widget.type}\n"
            widget_desc += f"Available events: {', '.join(widget.events)}\n"
            widget_desc += f"Methods triggered: {', '.join(widget.triggered_methods)}\n"
            widgets_info.append(widget_desc)

        return f"""
Current Window: {window.name}
Available Widgets:
{'\n'.join(widgets_info)}
"""

    def _format_target_methods(self,
                               target_methods: List[str],
                               coverage: Dict[str, float]) -> str:
        methods_info = []
        for method in target_methods:
            current_coverage = coverage.get(method, 0.0)
            methods_info.append(f"Method: {method} (Current coverage: {current_coverage}%)")

        return f"""
Target Methods to Cover:
{'\n'.join(methods_info)}
"""

    def _format_transitions(self,
                            wtg: List[WTGTransition],
                            current_window: Window) -> str:
        possible_transitions = [
            t for t in wtg if t.source_window == current_window.name
        ]

        transitions_info = []
        for trans in possible_transitions:
            transitions_info.append(
                f"To {trans.target_window} via {trans.trigger_event} "
                f"on widget {trans.trigger_widget}"
            )

        return f"""
Possible Navigation Paths:
{'\n'.join(transitions_info)}
"""

    def generate_prompt(self, static_data: StaticAnalysisData) -> str:
        context = self.create_context(static_data)

        prompt_template = f"""
Based on the following app analysis:

{context}

Generate a sequence of test actions that will:
1. Effectively test the current window
2. Maximize coverage of target methods
3. Navigate to unexplored windows when appropriate

The actions should be in the following format:
- For clicks: click(widget_id)
- For text input: setText(widget_id, "text")
- For scrolling: scroll(DIRECTION)

Consider:
- Target methods that need coverage improvement
- Available widgets and their events
- Possible navigation paths to other windows
- Current window state and layout

Provide a sequence of actions that will effectively test the application.
"""
        return prompt_template


class PromptEvaluator:
    def evaluate_prompt(self,
                        prompt: str,
                        static_data: StaticAnalysisData) -> float:
        score = 0.0
        max_score = 5.0

        # Verifica menção aos métodos alvo
        target_methods_mentioned = sum(
            1 for method in static_data.target_methods if method in prompt
        ) / len(static_data.target_methods)
        score += target_methods_mentioned

        # Verifica cobertura de widgets disponíveis
        widgets_mentioned = sum(
            1 for widget in static_data.current_window.widgets
            if widget.id in prompt
        ) / len(static_data.current_window.widgets)
        score += widgets_mentioned

        # Verifica menção a transições possíveis
        transitions_mentioned = sum(
            1 for trans in static_data.wtg
            if trans.source_window == static_data.current_window.name
            and trans.trigger_widget in prompt
        ) / len([t for t in static_data.wtg
                 if t.source_window == static_data.current_window.name])
        score += transitions_mentioned

        # Verifica formato das ações
        if "click(" in prompt and "setText(" in prompt:
            score += 1

        # Verifica estrutura e clareza
        if prompt.count("\n") > 5 and len(prompt) > 200:
            score += 1

        return score / max_score



def generate_prompt(classes: Classes, windows: Windows, wtg: WindowTransitionGraph, doirdbot_state: ScreenDescription):
    pass