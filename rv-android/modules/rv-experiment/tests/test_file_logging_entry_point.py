"""The run's log reaches disk (INV-CORE-62, task 5.5).

`LoggingManager.setup_file_logging` had no production caller. Its only call site,
`manager.py:147`, sits under `if self.log_path:` and `log_path` is assigned only
inside `setup_file_logging` — a guard that can never be true unless the method has
already run. Its own caller, `configure_output`, had two production callers and
both passed `file=False`.

The consequence this change cares about: `StaticAnalyzer.analyze()` logs the
effective scope key at INFO, and that line reached no file at all. A run's key was
therefore recoverable from nothing — not the artefact (which records the manifest
package), not the config, not the log.
"""

import logging

import pytest
from rv_android_core.util.logging.manager import LoggingManager


@pytest.fixture
def manager(tmp_path):
    """A LoggingManager with its singleton state reset around the test.

    The class is a process-wide singleton holding root-logger handlers, so a test
    that installs a file handler and walks away pollutes every later test in the
    session.
    """
    instance = LoggingManager.get_instance()
    previous_handlers = list(instance.root_logger.handlers)
    previous_path = instance.log_path
    yield instance
    for handler in list(instance.root_logger.handlers):
        if handler not in previous_handlers:
            instance.root_logger.removeHandler(handler)
            handler.close()
    instance.log_path = previous_path


class TestFileLoggingInstalledAtEntryPoint:
    def test_the_entry_point_has_a_production_caller(self):
        """The repair had to *create* the call, not re-enable one."""
        from rv_experiment.__main__ import CLIContext

        assert hasattr(CLIContext, "enable_file_logging")

        source = CLIContext.enable_file_logging.__doc__ or ""
        assert "INV-CORE-62" in source or "setup_file_logging" in source

    def test_the_run_installs_a_file_handler(self, manager, tmp_path):
        from rv_experiment.__main__ import CLIContext

        context = CLIContext()
        context.enable_file_logging(str(tmp_path / "results"), "exp_test")

        handlers = [
            handler
            for handler in context.logging_manager.root_logger.handlers
            if isinstance(handler, logging.FileHandler)
        ]
        assert handlers, "no file handler was installed"
        assert context.logging_manager.log_path is not None
        assert context.logging_manager.log_path.startswith(str(tmp_path / "results"))

    def test_the_effective_key_appears_in_the_run_log(self, manager, tmp_path):
        """The line `StaticAnalyzer.analyze()` writes at INFO, on disk.

        Asserted through a logger obtained the way the analyzer obtains one, so
        the test exercises the handler installation rather than a hand-built
        FileHandler.
        """
        from rv_experiment.__main__ import CLIContext

        context = CLIContext()
        context.enable_file_logging(str(tmp_path / "results"), "exp_key")
        manager = context.logging_manager

        logger = manager.get_logger(
            "rv_static_analysis.analysis.static.static_analysis.StaticAnalyzer"
        )
        logger.info(
            "Starting static analysis",
            extra={
                "code_package": "br.com.colman.petals",
                "code_package_source": "manifest-neutralized",
            },
        )
        # Only this run's handler: earlier tests in the module leave file
        # handlers on the singleton whose streams pytest has already closed, and
        # flushing one of those raises rather than reporting anything.
        for handler in manager.root_logger.handlers:
            if (
                isinstance(handler, logging.FileHandler)
                and handler.baseFilename == manager.log_path
            ):
                handler.flush()

        with open(manager.log_path, encoding="utf-8") as handle:
            written = handle.read()

        assert "Starting static analysis" in written
        # The file formatter shows structured context, so the key itself reaches
        # disk and not merely the sentence around it — which is what INV-CORE-62
        # is for. A message without its `extra` would record that an analysis
        # started and nothing about what it scoped by.
        assert "code_package=br.com.colman.petals" in written
        assert "code_package_source=manifest-neutralized" in written
