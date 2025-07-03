# Legacy Python < 3.3 support code removed from Command class
# This code was removed during architecture unification in Phase 1B

# Imports needed for legacy support
from threading import Timer

# Legacy Python support code block (lines 237-264 from original command.py)
def legacy_python_invoke(self, stdout=PIPE, stderr=PIPE, stdin=None):
    """
    Legacy implementation for Python < 3.3 without built-in timeout support.
    This code has been removed from the main Command class to modernize the codebase.
    """
    cmd_args = [self.command, *self.args]
    cmd_str = ' '.join(cmd_args)

    # Normalize stdin if it's a string
    if isinstance(stdin, str):
        stdin = stdin.encode()

    # Legacy Python support
    try:
        proc = Popen(cmd_args, stderr=stderr, stdout=stdout)

        # Setup timer for timeout if specified
        if self.timeout is not None:
            timer = Timer(self.timeout, self.kill_process, [proc])
            timer.start()

        stdout_data, stderr_data = proc.communicate(stdin)

        # Cancel timer if it's still running
        if self.timeout is not None:
            timer.cancel()

        self.logger.debug(LOG_COMPLETE.format(
            phase=f"command with exit code {proc.returncode}"
        ))

        return CommandResult(proc.returncode, stdout_data, stderr_data)

    except OSError as e:
        self.logger.error(LOG_ERROR.format(
            phase=f"executing command {cmd_str}",
            error=str(e)
        ))
        raise CommandNotFoundError(f"The command {self.command} was not found")