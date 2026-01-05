"""
Shared fixtures for integration tests.

Provides reusable components for testing RVAgentStrategy and related modules.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any

from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_screen_parser.parser.screen.visitor.model import WidgetEventType


@dataclass
class MockItemAction:
    """
    Mock ItemAction for testing.

    Simulates the ItemAction from rv_screen_parser with all necessary attributes.
    """
    event: WidgetEventType = WidgetEventType.CLICK
    coordinates: Tuple[int, int] = (540, 960)
    widget_id: Optional[str] = None
    text: str = ""
    directly_reaches_mop: bool = False
    reaches_mop: bool = False
    callback_signature: Optional[str] = None
    text_input: Optional[str] = None

    @property
    def coords_for_matching(self) -> Tuple[Tuple[int, int], str]:
        """Return coordinate signature for action matching."""
        return (self.coordinates, self.event.value)

    def get_execution_coordinates(self) -> Optional[Tuple[int, int]]:
        """Return coordinates for action execution."""
        return self.coordinates


@dataclass
class MockScreenItem:
    """Mock screen item containing view and actions."""
    view: dict = field(default_factory=lambda: {
        'class': 'android.widget.Button',
        'clickable': True,
        'bounds': [(100, 200), (300, 400)],
        'resource_id': '',
        'text': ''
    })
    actions: List[MockItemAction] = field(default_factory=list)


@dataclass
class MockScreenDescription:
    """
    Mock ScreenDescription for testing.

    Simulates the ScreenDescription from rv_screen_parser.
    """
    activity: str = "MainActivity"
    items: List[MockScreenItem] = field(default_factory=list)

    def get_all_actions(self) -> List[MockItemAction]:
        """Return all actions from all items."""
        actions = []
        for item in self.items:
            actions.extend(item.actions)
        return actions


def create_mock_action(
    coords: Tuple[int, int] = (540, 960),
    event_type: WidgetEventType = WidgetEventType.CLICK,
    widget_id: Optional[str] = None,
    directly_reaches_mop: bool = False,
    reaches_mop: bool = False,
    callback_signature: Optional[str] = None
) -> MockItemAction:
    """Factory function to create mock actions."""
    return MockItemAction(
        event=event_type,
        coordinates=coords,
        widget_id=widget_id,
        directly_reaches_mop=directly_reaches_mop,
        reaches_mop=reaches_mop,
        callback_signature=callback_signature
    )


def create_mock_screen(
    activity: str,
    actions: List[MockItemAction]
) -> MockScreenDescription:
    """Factory function to create mock screen descriptions."""
    items = []
    for action in actions:
        item = MockScreenItem(
            view={
                'class': 'android.widget.Button',
                'clickable': True,
                'bounds': [(action.coordinates[0]-50, action.coordinates[1]-50),
                          (action.coordinates[0]+50, action.coordinates[1]+50)],
                'resource_id': action.widget_id or '',
                'text': action.text
            },
            actions=[action]
        )
        items.append(item)

    return MockScreenDescription(activity=activity, items=items)


@pytest.fixture
def dynamic_graph():
    """Provide fresh DynamicStateGraph instance."""
    return DynamicStateGraph()


@pytest.fixture
def ui_coverage():
    """Provide fresh UICoverageTracker instance."""
    return UICoverageTracker()


@pytest.fixture
def rvagent_strategy(dynamic_graph, ui_coverage):
    """Provide configured RVAgentStrategy instance."""
    return RVAgentStrategy(
        graph=dynamic_graph,
        ui_coverage=ui_coverage,
        plateau_window=5,
        max_input_variations=3
    )


@pytest.fixture
def simple_screen():
    """Provide a simple screen with 3 clickable buttons."""
    return create_mock_screen(
        activity="MainActivity",
        actions=[
            create_mock_action(coords=(200, 400), widget_id="btn_login"),
            create_mock_action(coords=(200, 600), widget_id="btn_register"),
            create_mock_action(coords=(200, 800), widget_id="btn_settings"),
        ]
    )


@pytest.fixture
def mop_priority_screen():
    """Provide a screen with MOP-reaching actions for priority testing."""
    return create_mock_screen(
        activity="CryptoActivity",
        actions=[
            create_mock_action(
                coords=(200, 400),
                widget_id="btn_encrypt",
                directly_reaches_mop=True,
                callback_signature="javax.crypto.Cipher.init"
            ),
            create_mock_action(
                coords=(200, 600),
                widget_id="btn_settings",
                reaches_mop=True
            ),
            create_mock_action(
                coords=(200, 800),
                widget_id="btn_help"
            ),
        ]
    )


@pytest.fixture
def input_screen():
    """Provide a screen with text input fields."""
    return create_mock_screen(
        activity="LoginActivity",
        actions=[
            create_mock_action(
                coords=(200, 400),
                event_type=WidgetEventType.TEXT_CHANGE,
                widget_id="input_username"
            ),
            create_mock_action(
                coords=(200, 600),
                event_type=WidgetEventType.TEXT_CHANGE,
                widget_id="input_password"
            ),
            create_mock_action(
                coords=(200, 800),
                widget_id="btn_submit"
            ),
        ]
    )


@pytest.fixture
def dropdown_screen():
    """Provide a screen simulating a dropdown menu."""
    return create_mock_screen(
        activity="DropdownActivity",
        actions=[
            create_mock_action(coords=(200, 400), widget_id="option_1"),
            create_mock_action(coords=(200, 500), widget_id="option_2"),
            create_mock_action(coords=(200, 600), widget_id="option_3"),
        ]
    )
