#!/usr/bin/env python3
"""
Quick test for NavigationGuidance with real static analysis data.

Tests that the integration between TransitionManager and NavigationGuidance
works correctly to provide exploration hints.
"""

import sys
sys.path.insert(0, "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/src")
sys.path.insert(0, "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-android-core/src")
sys.path.insert(0, "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-static-analysis/src")
sys.path.insert(0, "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-screen-parser/src")

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')


def main():
    print("=" * 60)
    print("NavigationGuidance Test with Real Static Data")
    print("=" * 60)

    # 1. Load static analysis data
    print("\n1. Loading static analysis data...")

    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

    parser = StaticAnalysisParser()

    base_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk"

    static_data = parser.parse(
        reach_file=f"{base_path}/cryptoapp.apk.reach",
        gator_file=f"{base_path}/cryptoapp.apk.wtg",  # WTG is from gator
        gesda_file=f"{base_path}/cryptoapp.apk.gesda",
        package="com.example.cryptoapp"
    )

    print(f"   Classes: {len(static_data.classes.classes)}")
    print(f"   Windows: {len(static_data.windows.windows)}")
    print(f"   WTG: {'Available' if static_data.wtg else 'Not available'}")

    if static_data.wtg:
        print(f"   WTG transitions: {len(static_data.wtg.transitions) if hasattr(static_data.wtg, 'transitions') else 'N/A'}")

    # List windows
    print("\n   Windows found:")
    windows_list = list(static_data.windows.windows)
    for window in windows_list[:5]:
        print(f"     - {window.name} (id={window.id})")
    if len(windows_list) > 5:
        print(f"     ... and {len(windows_list) - 5} more")

    # 2. Create DynamicStateGraph
    print("\n2. Creating DynamicStateGraph...")

    from rv_agent.agent.dynamic_state_graph import DynamicStateGraph

    dynamic_graph = DynamicStateGraph()
    print(f"   States: {len(dynamic_graph.states)}")

    # 3. Create TransitionManager
    print("\n3. Creating TransitionManager...")

    from rv_agent.services.transition_manager import TransitionManager

    transition_manager = TransitionManager(
        static_data=static_data,
        dynamic_graph=dynamic_graph
    )
    print("   TransitionManager created successfully")

    # 4. Create NavigationGuidance
    print("\n4. Creating NavigationGuidance...")

    from rv_agent.services.navigation_guidance import NavigationGuidance

    nav_guidance = NavigationGuidance(transition_manager=transition_manager)
    print(f"   Enabled: {nav_guidance.is_enabled}")

    # 5. Create a mock ScreenDescription
    print("\n5. Creating mock ScreenDescription...")

    from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem, ItemAction
    from rv_android_core.domain.widget import WidgetEventType

    # Use MainActivity which should have transitions
    first_activity = "br.unb.cic.cryptoapp.MainActivity"

    print(f"   Simulating activity: {first_activity}")

    # Create mock screen description
    mock_action = ItemAction(
        id=1,
        text="Click on Encrypt button",
        event=WidgetEventType.CLICK,
        target_view={
            "class": "android.widget.Button",
            "resource_id": "btn_encrypt",
            "text": "Encrypt",
            "bounds": [[100, 500], [600, 700]]
        },
        coordinates=(350, 600)
    )

    mock_item = ScreenItem(
        view={
            "class": "android.widget.Button",
            "resource_id": "btn_encrypt",
            "text": "Encrypt"
        },
        base_description="Encrypt button",
        actions=[mock_action]
    )

    mock_screen = ScreenDescription(
        activity=first_activity,
        items=[mock_item]
    )

    # 6. Get exploration context
    print("\n6. Getting exploration context...")

    context = nav_guidance.get_context(mock_screen)

    print(f"   Has guidance: {context.has_guidance}")
    print(f"   Unvisited screens: {len(context.unvisited_screens)}")
    print(f"   Suggested actions: {len(context.suggested_actions)}")
    print(f"   Priority targets: {len(context.priority_targets)}")

    if context.unvisited_screens:
        print("\n   Unvisited screens:")
        for screen in context.unvisited_screens[:5]:
            print(f"     - {screen}")

    if context.suggested_actions:
        print("\n   Suggested actions:")
        for action in context.suggested_actions[:3]:
            print(f"     - {action.get('action_type', 'click')} on '{action.get('action_text', 'element')}' -> {action.get('target_activity', 'unknown')}")

    # 7. Format for LLM
    print("\n7. Formatting for LLM...")

    llm_hint = nav_guidance.format_for_llm(context)
    compact_hint = nav_guidance.format_for_llm_compact(context)

    print("\n   Full format:")
    if llm_hint:
        for line in llm_hint.split('\n'):
            print(f"   {line}")
    else:
        print("   (no guidance available)")

    print("\n   Compact format:")
    print(f"   {compact_hint if compact_hint else '(no guidance available)'}")

    # 8. Get summary
    print("\n8. Navigation summary...")

    summary = nav_guidance.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
