"""Parse UIAutomator XML dumps into Widget instances.

Replicates the widget extraction logic used by APE's ApePromptBuilder (commit b2852dd).
Filters: clickable + enabled + area > 0, excludes system UI nodes.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import defusedxml.ElementTree as ET

from aperv_llm_validation.constants import INPUT_CLASS_NAMES
from aperv_llm_validation.data.models import Widget

logger = logging.getLogger(__name__)

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")

_SYSTEM_UI_PACKAGE = "com.android.systemui"


def parse_uiautomator(xml_path: Path) -> list[Widget]:
    """Parse a .uiautomator XML file into a list of clickable Widget instances.

    Filtering rules:
    - clickable="true" AND enabled="true"
    - bounds area > 0
    - Not from system UI package (com.android.systemui)
    - resource-id does not start with "com.android.systemui"

    Returns empty list for malformed XML (logs warning).
    Raises FileNotFoundError if xml_path does not exist.
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"UIAutomator XML not found: {xml_path}")

    try:
        tree = ET.parse(str(xml_path))
    except Exception:
        logger.warning("Malformed UIAutomator XML: %s", xml_path)
        return []

    root = tree.getroot()
    widgets: list[Widget] = []

    for node in root.iter("node"):
        # Filter: must be clickable and enabled
        if node.get("clickable") != "true":
            continue
        if node.get("enabled") != "true":
            continue

        # Exclude system UI
        package = node.get("package", "")
        if package == _SYSTEM_UI_PACKAGE:
            continue
        resource_id = node.get("resource-id", "")
        if resource_id.startswith(_SYSTEM_UI_PACKAGE):
            continue

        # Parse bounds
        bounds_str = node.get("bounds", "")
        m = _BOUNDS_RE.match(bounds_str)
        if not m:
            continue
        left, top, right, bottom = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))

        # Filter: area > 0
        area = (right - left) * (bottom - top)
        if area <= 0:
            continue

        class_name = node.get("class", "android.view.View")
        text = node.get("text", "")
        content_desc = node.get("content-desc", "")
        long_clickable = node.get("long-clickable") == "true"
        checkable = node.get("checkable") == "true"
        editable = class_name in INPUT_CLASS_NAMES

        widget = Widget(
            class_name=class_name,
            text=text,
            content_desc=content_desc,
            resource_id=resource_id,
            bounds=(left, top, right, bottom),
            clickable=True,
            long_clickable=long_clickable,
            editable=editable,
            checkable=checkable,
            enabled=True,
        )
        widgets.append(widget)

    return widgets
