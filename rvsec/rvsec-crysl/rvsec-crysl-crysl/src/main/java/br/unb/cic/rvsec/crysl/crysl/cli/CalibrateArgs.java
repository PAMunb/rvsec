package br.unb.cic.rvsec.crysl.crysl.cli;

import com.beust.jcommander.Parameter;
import com.beust.jcommander.Parameters;

/**
 * Arguments of {@code calibrate}: the calibration gate, run on its own.
 *
 * <p>It is a separate subcommand rather than a flag on {@code compare} because a corpus move has to
 * be checkable without a full comparison run — that is most of what a calibration target is for.
 * And it takes the corpora rather than an emitted report because only three of the eight quantities
 * appear in a report at all: the others are about {@code generic} and {@code generic_new}, which
 * {@code compare} never reads, or about facts no emitted table carries.
 *
 * <p>The targets themselves are not a file. They are
 * {@link br.unb.cic.rvsec.crysl.core.calibration.CalibrationTargets}, compiled in, each with its
 * value, its counting rule and the repository and commit <em>its own route</em> was taken at. A
 * target is a claim about what an independent route measured; keeping it in a file anyone can edit
 * between two runs would make the gate's green a function of the file rather than of the component.
 */
@Parameters(commandDescription = "Run the calibration gate: measure the eight quantities and check "
        + "each against the independent route that produced its target")
class CalibrateArgs {

    @Parameter(names = {"--mop-root", "-m"},
            description = "The directory holding the five .mop corpora (jca, jca_android, "
                    + "jca_android_bug_predicate, generic, generic_new), read-only",
            required = true)
    String mopRoot;

    @Parameter(names = {"--rules-dir", "-r"},
            description = "The upstream CrySL-Rules oracle, read-only",
            required = true)
    String rulesDir;

    @Parameter(names = {"--commit", "-c"},
            description = "The rvsec commit this run reads the .mop corpora at. Printed beside "
                    + "each target's own stamp, so a corpus move is visible without archaeology",
            required = true)
    String commit;

    @Parameter(names = {"--oracle-commit", "-o"},
            description = "The rvsec-cognicrypt commit this run reads the oracle at. It moves on "
                    + "its own clock and is never the same field as --commit (D-17)",
            required = true)
    String oracleCommit;

    @Parameter(names = {"--monitor"},
            description = "A regenerated MultiSpec_1RuntimeMonitor.java. When given, target 8's "
                    + "route is re-taken from it at this run's stamp instead of being assumed to "
                    + "have carried from the commit it was pinned at")
    String monitor;
}
