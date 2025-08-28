# RV-UIAutomator

Shared UIAutomator components for RV-Android testing tools.

## Overview

This module provides shared UIAutomator components that can be used by multiple RV-Android testing tools, eliminating code duplication and providing consistent device interaction patterns.

## Components

- **UIAdapter**: Abstract interface for device interaction
- **UIAutomator2Adapter**: UIAutomator2 implementation
- **UIAutomatorActionExecutor**: Action execution engine
- **StateConverter**: State format conversion utilities

## Installation

This module is installed as part of the RV-Android workspace. Dependencies are managed through the parent workspace Poetry configuration.

## Usage

```python
from rv_uiautomator.adapter import UIAutomator2Adapter
from rv_uiautomator.executor import UIAutomatorActionExecutor

# Initialize adapter
adapter = UIAutomator2Adapter(device_id="emulator-5554")
adapter.connect("emulator-5554")

# Execute actions
executor = UIAutomatorActionExecutor()
executor.execute(action, adapter)
```