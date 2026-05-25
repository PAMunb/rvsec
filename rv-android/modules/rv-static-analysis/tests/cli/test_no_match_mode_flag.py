"""
INV-ANA-36 — no ``--match-mode`` / ``--matching`` / ``--lenient`` / ``--strict``
option is registered on the CLI.

The polymorphic source design rejects a global match-mode toggle: matching is
a per-entry property of each :class:`TargetMethod`, decided at load time by
the :class:`TargetMethodSource` impl. A global flag would re-introduce the
collision design.md §D7 explicitly closes.
"""

from rv_static_analysis.__main__ import setup_argument_parser


def test_no_match_mode_style_flag_registered() -> None:
    parser = setup_argument_parser()
    forbidden = {"--match-mode", "--matching", "--lenient", "--strict"}
    registered: set[str] = set()
    # The top-level parser has subparsers; walk them.
    for action in parser._actions:
        if isinstance(action.choices, dict):
            for sub in action.choices.values():
                for sub_action in sub._actions:
                    for opt in sub_action.option_strings:
                        registered.add(opt)
        for opt in action.option_strings:
            registered.add(opt)

    leaked = forbidden & registered
    assert not leaked, (
        "Forbidden match-mode flags are present on the CLI (INV-ANA-36); "
        f"matching MUST be a per-entry property of the TargetMethod, not a "
        f"global flag. Found: {sorted(leaked)}"
    )
