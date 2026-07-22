#!/usr/bin/env python3
"""
Trace logger hook for rv-android.
Logs tool calls, skill invocations, subagent lifecycle, and sessions
to output/trace.log in JSONL format.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path


def get_log_path():
    """Return log path in the project's output directory."""
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    log_dir = Path(project_dir) / 'output'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'trace.log'


def log_entry(entry: dict, raw_data: dict = None):
    """Append a JSONL entry to the trace log.
    Includes _raw_keys so we can detect undocumented fields."""
    log_path = get_log_path()
    entry['timestamp'] = datetime.now().isoformat()

    if raw_data:
        # Log ALL keys present in raw data so we never miss undocumented fields
        entry['_raw_keys'] = sorted(raw_data.keys())

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def handle_session_start(data: dict):
    """Log session start with model and source info."""
    log_entry({
        'event': 'SESSION_START',
        'session_id': data.get('session_id'),
        'source': data.get('source'),
        'model': data.get('model'),
        'cwd': data.get('cwd'),
        'transcript_path': data.get('transcript_path'),
        'permission_mode': data.get('permission_mode'),
    }, raw_data=data)


def handle_session_end(data: dict):
    """Log session end with reason."""
    log_entry({
        'event': 'SESSION_END',
        'session_id': data.get('session_id'),
        'reason': data.get('reason'),
    }, raw_data=data)


def handle_pre_tool_use(data: dict):
    """Log before a tool call."""
    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})

    info = {}

    if tool_name == 'Read':
        info['file_path'] = tool_input.get('file_path')
        info['offset'] = tool_input.get('offset')
        info['limit'] = tool_input.get('limit')
    elif tool_name in ('Write', 'Edit'):
        info['file_path'] = tool_input.get('file_path')
    elif tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        info['command_preview'] = cmd[:200] + ('...' if len(cmd) > 200 else '')
    elif tool_name == 'Task':
        info['subagent_type'] = tool_input.get('subagent_type')
        info['description'] = tool_input.get('description')
        info['model'] = tool_input.get('model')
    elif tool_name == 'Skill':
        info['skill'] = tool_input.get('skill')
        info['args'] = tool_input.get('args')
    elif tool_name == 'Glob':
        info['pattern'] = tool_input.get('pattern')
        info['path'] = tool_input.get('path')
    elif tool_name == 'Grep':
        info['pattern'] = tool_input.get('pattern')
        info['path'] = tool_input.get('path')
    elif tool_name.startswith('mcp__'):
        parts = tool_name.split('__')
        info['mcp_server'] = parts[1] if len(parts) > 1 else 'unknown'
        info['mcp_tool'] = parts[2] if len(parts) > 2 else 'unknown'

    log_entry({
        'event': 'PRE_TOOL_USE',
        'session_id': data.get('session_id'),
        'tool_name': tool_name,
        'tool_use_id': data.get('tool_use_id'),
        'agent_id': data.get('agent_id'),
        'permission_mode': data.get('permission_mode'),
        'transcript_path': data.get('transcript_path'),
        **info,
    }, raw_data=data)


def handle_post_tool_use(data: dict):
    """Log after a successful tool call."""
    tool_name = data.get('tool_name', '')
    tool_response = data.get('tool_response', {})

    info = {}

    if tool_name in ('Write', 'Edit'):
        info['success'] = tool_response.get('success')
        info['file_path'] = tool_response.get('filePath')
    elif tool_name == 'Read':
        info['success'] = True
    elif tool_name == 'Bash':
        info['exit_code'] = tool_response.get('exitCode')
    elif tool_name == 'Task':
        info['subagent_type'] = tool_response.get('subagent_type')
    elif tool_name == 'Skill':
        info['skill'] = tool_response.get('skill')
    elif tool_name.startswith('mcp__'):
        parts = tool_name.split('__')
        info['mcp_server'] = parts[1] if len(parts) > 1 else 'unknown'
        info['mcp_tool'] = parts[2] if len(parts) > 2 else 'unknown'
        if isinstance(tool_response, dict):
            info['status'] = tool_response.get('status')

    log_entry({
        'event': 'POST_TOOL_USE',
        'session_id': data.get('session_id'),
        'tool_name': tool_name,
        'tool_use_id': data.get('tool_use_id'),
        'agent_id': data.get('agent_id'),
        'permission_mode': data.get('permission_mode'),
        'transcript_path': data.get('transcript_path'),
        **info,
    }, raw_data=data)


def handle_post_tool_use_failure(data: dict):
    """Log tool call failure."""
    log_entry({
        'event': 'POST_TOOL_USE_FAILURE',
        'session_id': data.get('session_id'),
        'tool_name': data.get('tool_name'),
        'tool_use_id': data.get('tool_use_id'),
        'error': data.get('error'),
        'is_interrupt': data.get('is_interrupt'),
        'permission_mode': data.get('permission_mode'),
        'transcript_path': data.get('transcript_path'),
    }, raw_data=data)


def handle_user_prompt_submit(data: dict):
    """Log user prompt submission with a preview of the prompt text."""
    prompt = data.get('prompt', '')
    log_entry({
        'event': 'USER_PROMPT_SUBMIT',
        'session_id': data.get('session_id'),
        'prompt_preview': prompt[:200] + ('...' if len(prompt) > 200 else ''),
    }, raw_data=data)


def handle_subagent_start(data: dict):
    """Log subagent spawn with agent_id and type."""
    log_entry({
        'event': 'SUBAGENT_START',
        'session_id': data.get('session_id'),
        'agent_id': data.get('agent_id'),
        'agent_type': data.get('agent_type'),
        'permission_mode': data.get('permission_mode'),
        'transcript_path': data.get('transcript_path'),
    }, raw_data=data)


def handle_subagent_stop(data: dict):
    """Log subagent completion with transcript path."""
    log_entry({
        'event': 'SUBAGENT_STOP',
        'session_id': data.get('session_id'),
        'agent_id': data.get('agent_id'),
        'agent_type': data.get('agent_type'),
        'agent_transcript_path': data.get('agent_transcript_path'),
        'stop_hook_active': data.get('stop_hook_active'),
        'permission_mode': data.get('permission_mode'),
        'transcript_path': data.get('transcript_path'),
    }, raw_data=data)


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)

    event = data.get('hook_event_name', '')

    handlers = {
        'SessionStart': handle_session_start,
        'SessionEnd': handle_session_end,
        'UserPromptSubmit': handle_user_prompt_submit,
        'PreToolUse': handle_pre_tool_use,
        'PostToolUse': handle_post_tool_use,
        'PostToolUseFailure': handle_post_tool_use_failure,
        'SubagentStart': handle_subagent_start,
        'SubagentStop': handle_subagent_stop,
    }

    handler = handlers.get(event)
    if handler:
        handler(data)

    # Exit 0 = success, non-blocking
    sys.exit(0)


if __name__ == '__main__':
    main()
