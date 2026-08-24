"""Module-specific exceptions for the DEX-native wrapper.

Raised by prepare_instrumentation / instrument / instrument_apks; consumers
catch them (or the underlying CommandException from the Java CLI subprocess)
and populate InstrumentationResults.errors with a phase tag.
"""


class MissingDescriptorError(Exception):
    """No MultiSpec_*MonitorAspect.json found in monitor_output_dir.

    Raised at preparation time, before any APK is processed (INV-INS-50).
    The message identifies the missing file and mentions the
    ``--emit-descriptor`` flag that rv-monitor-generator must pass to JavaMOP
    for the dexlib2 variant to work.
    """


class DescriptorParseError(Exception):
    """The JSON descriptor exists but Jackson failed to deserialize it.

    Raised by the Java CLI subprocess and surfaced through the Python wrapper
    with the JSON pointer that Jackson captured (e.g.
    ``AspectDescriptor["advices"]->AdviceDescriptor["isAround"]``).
    """


class UnsupportedAspectConstructError(Exception):
    """A descriptor advice references an AspectJ construct the weaver does not support.

    The canonical out-of-scope set is documented in
    ``rv-android/docs/LIMITATIONS.md``: ``around``, ``cflow``, ``cflowbelow``,
    ``handler``, ``get``, ``set``, ``initialization``, ``preinitialization``.
    Empirical evidence confirms zero usages of these in the RVSEC spec corpus
    (both JCA and Generic sets) so the error indicates a spec change that
    invalidates the scope assumption.
    """
