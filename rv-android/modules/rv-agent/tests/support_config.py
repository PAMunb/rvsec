"""Shared RVAgentConfig factories for the rv-agent test suite.

A single source of test configs so that adding a field to `RVAgentConfig`
never forces edits across many test helpers. This matters most for the
`arm_defining` steering flags: the scoring pipeline calls
`scorer.is_enabled(config)` for every scorer, and a scorer that reads a new
flag (e.g. a numeric weight compared with `> 0`) would break any per-attribute
`MagicMock` config that had not been taught about that field. Both factories
below source every field from the model's own defaults, so a new flag is
covered the moment it is declared on `RVAgentConfig`.

Two factories, picked by what the test needs:

- `make_agent_config`  — a real `RVAgentConfig`. Preferred: the strategy and
  scorers read it purely as a data holder, and a real instance exercises the
  same validation and defaults as production.
- `make_config_mock`   — a `MagicMock(spec=RVAgentConfig)` pre-seeded with
  every real field value. Use only when the test needs mock semantics on the
  config object itself (patched methods such as `get_agent_mode`, or call
  assertions) while still reading real defaults for every field.

Importable as a top-level module because `conftest.py` adds the `tests/`
directory to `sys.path` (see conftest.py) before any test module is imported.
"""

from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig

# Only `package_name` is required by RVAgentConfig; everything else defaults.
_DEFAULT_PACKAGE = "com.test.app"


def make_agent_config(package_name: str = _DEFAULT_PACKAGE, **overrides) -> RVAgentConfig:
    """Build a real `RVAgentConfig` with test defaults and optional overrides.

    Every field (including every steering flag) comes from the model's own
    defaults, so new flags need no change here. Overrides are validated by
    Pydantic exactly as production construction would validate them.
    """
    return RVAgentConfig(package_name=package_name, **overrides)


def make_config_mock(package_name: str = _DEFAULT_PACKAGE, **overrides) -> MagicMock:
    """Build a `MagicMock(spec=RVAgentConfig)` seeded with real field values.

    Construct a real config first, copy each of its fields onto the mock, then
    apply overrides. Methods remain auto-specced mocks, so a test can still set
    e.g. `config.get_agent_mode.return_value = ...` or assert on calls.
    """
    real = RVAgentConfig(package_name=package_name)
    mock = MagicMock(spec=RVAgentConfig)
    for name, value in real.model_dump().items():
        setattr(mock, name, value)
    for name, value in overrides.items():
        setattr(mock, name, value)
    return mock
