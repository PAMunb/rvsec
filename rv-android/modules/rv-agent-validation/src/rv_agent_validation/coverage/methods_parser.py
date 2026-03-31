"""
Parser for .methods files containing static analysis data.

Reads method coverage data and builds signature lookup tables.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Set


@dataclass
class MethodData:
    """Method information from .methods file."""

    class_name: str
    name: str
    parameters: str
    signature: str  # Full signature: class.method(params)
    component_type: str
    reachable: bool
    reaches_mop: bool
    directly_reaches_mop: bool


class MethodsParser:
    """
    Parser for .methods files.

    Builds lookup tables for method signatures and calculates totals.
    """

    def __init__(self, file_path: Path):
        """
        Initialize parser with .methods file.

        Args:
            file_path: Path to .methods file
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Methods file not found: {file_path}")

        self.file_path = file_path
        self.apk_name = file_path.stem

        # Lookup tables
        self.methods: Dict[str, MethodData] = {}
        self.signatures: Set[str] = set()
        self.classes: Set[str] = set()
        self.activities: Set[str] = set()

        # Totals
        self.total_methods = 0
        self.reachable_count = 0
        self.reaches_mop_count = 0
        self.directly_reaches_mop_count = 0

        self._parse()

    def _parse(self) -> None:
        """Parse .methods file and build lookup tables."""
        with open(self.file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build full signature: class.method(params)
                signature = f"{row['class']}.{row['signature']}"

                method = MethodData(
                    class_name=row["class"],
                    name=row["method"],
                    parameters=row["parameters"],
                    signature=signature,
                    component_type=row.get("component_type", row.get("is_activity", "")),
                    reachable=row["reachable"].lower() == "true",
                    reaches_mop=row["reaches_mop"].lower() == "true",
                    directly_reaches_mop=row["directly_reaches_mop"].lower() == "true",
                )

                # Add to lookup tables
                self.methods[signature] = method
                self.signatures.add(signature)
                self.classes.add(method.class_name)

                if method.component_type == "activity":
                    self.activities.add(method.class_name)

                # Update totals
                self.total_methods += 1
                if method.reachable:
                    self.reachable_count += 1
                if method.reaches_mop:
                    self.reaches_mop_count += 1
                if method.directly_reaches_mop:
                    self.directly_reaches_mop_count += 1

    def get_method(self, signature: str) -> Optional[MethodData]:
        """Get method by signature."""
        return self.methods.get(signature)

    def has_signature(self, signature: str) -> bool:
        """Check if signature exists."""
        return signature in self.signatures

    def __repr__(self) -> str:
        return (
            f"MethodsParser({self.apk_name}: "
            f"{self.total_methods} methods, "
            f"{len(self.classes)} classes, "
            f"{len(self.activities)} activities)"
        )
