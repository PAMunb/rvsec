# rvandroid/experiment/event/constants.py
"""
Event name constants for the RV-Android system.

This module defines constant string values for all standard events used
throughout the framework. These constants should be used instead of
hardcoded strings to ensure consistency and avoid typos.
"""

# Orchestration events
ORCHESTRATION_EVENT = "orchestration.event"

# Task lifecycle events
TASK_CREATED = "task.created"
TASK_CONFIGURED = "task.configured"
TASK_STARTED = "task.started"
TASK_COMPLETED = "task.completed"
TASK_FAILED = "task.failed"

# Experiment lifecycle events
EXPERIMENT_STARTED = "experiment.started"
EXPERIMENT_COMPLETED = "experiment.completed"
EXPERIMENT_FAILED = "experiment.failed"
EXPERIMENT_PAUSED = "experiment.paused"
EXPERIMENT_RESUMED = "experiment.resumed"

# Workflow lifecycle events
WORKFLOW_STARTED = "workflow.started"
WORKFLOW_COMPLETED = "workflow.completed"
WORKFLOW_FAILED = "workflow.failed"
WORKFLOW_PAUSED = "workflow.paused"
WORKFLOW_RESUMED = "workflow.resumed"

# Phase lifecycle events
PHASE_STARTED = "phase.started"
PHASE_COMPLETED = "phase.completed"
PHASE_FAILED = "phase.failed"
PHASE_SKIPPED = "phase.skipped"

# Analysis events
COVERAGE_UPDATED = "analysis.coverage.updated"
COVERAGE_TRACKING_STARTED = "analysis.coverage.started"
COVERAGE_TRACKING_STOPPED = "analysis.coverage.stopped"
ERROR_DETECTED = "analysis.error.detected"
STATIC_ANALYSIS_COMPLETED = "analysis.static.completed"
NEW_METHOD_DISCOVERED = "analysis.method.discovered"

# Environment lifecycle events
EMULATOR_STARTED = "environment.emulator.started"
EMULATOR_STOPPED = "environment.emulator.stopped"
APP_INSTALLED = "environment.app.installed"
TOOL_STARTED = "environment.tool.started"
TOOL_STOPPED = "environment.tool.stopped"

# Configuration events
CONFIG_LOADED = "config.loaded"
CONFIG_SAVED = "config.saved"

# Event channels
CHANNEL_TASK = "task"
CHANNEL_EXPERIMENT = "experiment"
CHANNEL_WORKFLOW = "workflow"
CHANNEL_ANALYSIS = "analysis"
CHANNEL_ENVIRONMENT = "environment"
CHANNEL_CONFIG = "config"