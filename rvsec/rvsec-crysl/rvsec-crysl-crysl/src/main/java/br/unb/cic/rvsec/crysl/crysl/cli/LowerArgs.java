package br.unb.cic.rvsec.crysl.crysl.cli;

import com.beust.jcommander.Parameter;
import com.beust.jcommander.Parameters;

/**
 * Arguments of {@code lower}: {@code mop.lower} — model to {@code .mop} text — followed by the
 * round-trip gate on what came out.
 *
 * <p>{@code --commit} and {@code --corpus} are mandatory here for the same reason as in
 * {@code compare}: a lowered file that does not say which corpus state it was lowered from cannot
 * be compared to the file it came from a week later.
 *
 * <p>The gate reads a rule and an API index as well, and those arguments are not declared yet: the
 * lowering and gate code is a separate task group, and inventing its input surface before it exists
 * would fix a contract the group has not written. When that group lands it adds {@code --rules-dir}
 * and {@code --android-jar} here, matching {@link CompareArgs}.
 */
@Parameters(commandDescription = "Lower lifted models back to .mop text and run the round-trip gate")
class LowerArgs {

    @Parameter(names = {"--mop-dir", "-m"},
            description = "Directory of JavaMOP specifications (*.mop) to lift and lower",
            required = true)
    String mopDir;

    @Parameter(names = {"--corpus", "-c"},
            description = "Name of the .mop corpus being lowered, e.g. jca_android",
            required = true)
    String corpus;

    @Parameter(names = {"--commit"},
            description = "Commit of the rvsec repository the corpus was read at; no default, no "
                    + "detection from git",
            required = true)
    String commit;

    @Parameter(names = {"--out", "-o"},
            description = "Directory the lowered .mop files and the gate verdicts are written to",
            required = true)
    String outputDir;
}
