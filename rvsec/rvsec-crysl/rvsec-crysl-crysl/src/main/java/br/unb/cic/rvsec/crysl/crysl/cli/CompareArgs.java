package br.unb.cic.rvsec.crysl.crysl.cli;

import com.beust.jcommander.Parameter;
import com.beust.jcommander.Parameters;

/**
 * Arguments of {@code compare}: the M0–M4 run of one {@code .mop} corpus against the upstream
 * oracle.
 *
 * <p><strong>One oracle.</strong> There is a single {@code --rules-dir} and no switch that would
 * add a second, because there is no two-oracle mode to offer (D-06). The generated {@code api30}
 * corpus is not an oracle: measured against upstream it deletes 25 {@code CONSTRAINTS} clauses
 * across 12 of the 22 paired rules, so a specification faithful to the upstream rule would be
 * accused of implementing clauses "without base". Adding an {@code --oracle} selector here is what
 * would make that mistake available again.
 *
 * <p><strong>Two commits, both mandatory, neither inferred.</strong> The input spans two git
 * repositories — {@code rvsec} for the {@code .mop} sets and {@code rvsec-cognicrypt} for the rules
 * — so one commit field cannot stamp the run (INV-CONF-01). Neither is defaulted and neither is
 * read out of {@code git}: an auto-detected commit is the tool's inference about a working tree it
 * cannot see the cleanliness of, and a wrong stamp derived that way looks exactly like a right one.
 * Required and explicit makes a wrong stamp the caller's assertion instead.
 *
 * <p><strong>The corpus name is given, not derived from the directory.</strong> {@code jca} and
 * {@code jca_android} differ by a directory name today and that is an accident of layout; a number
 * attributed to the wrong set because someone copied a directory is not recoverable after the fact.
 */
@Parameters(commandDescription = "Compare a .mop corpus against the upstream CrySL rules (M0-M4)")
class CompareArgs {

    @Parameter(names = {"--mop-dir", "-m"},
            description = "Directory of JavaMOP specifications (*.mop) to measure",
            required = true)
    String mopDir;

    @Parameter(names = {"--corpus", "-c"},
            description = "Name of the .mop corpus being measured, e.g. jca_android. Stamped into "
                    + "every emitted table; never derived from the directory name",
            required = true)
    String corpus;

    @Parameter(names = {"--commit"},
            description = "Commit of the rvsec repository the .mop corpus was read at. No default "
                    + "and no detection from git: the caller asserts which corpus state is measured",
            required = true)
    String commit;

    @Parameter(names = {"--rules-dir", "-r"},
            description = "The single oracle: rvsec-cognicrypt/CrySL-Rules, read-only",
            required = true)
    String rulesDir;

    @Parameter(names = {"--oracle-commit"},
            description = "Commit of the rvsec-cognicrypt repository the rules were read at. "
                    + "Separate from --commit because the two corpora are two repositories",
            required = true)
    String oracleCommit;

    @Parameter(names = {"--alphabet", "-a"},
            description = "order_alphabet_map.csv, which declares the label/signature pairing and "
                    + "the epsilon-erasure disposition per event",
            required = true)
    String alphabetMap;

    @Parameter(names = {"--android-jar", "-j"},
            description = "android.jar used as an a-posteriori index only; never placed on any "
                    + "parser classpath",
            required = true)
    String androidJar;

    @Parameter(names = {"--out", "-o"},
            description = "Directory the JSON, CSV and Markdown outputs are written to",
            required = true)
    String outputDir;
}
