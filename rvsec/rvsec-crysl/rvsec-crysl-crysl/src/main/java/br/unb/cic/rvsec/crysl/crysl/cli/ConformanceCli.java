package br.unb.cic.rvsec.crysl.crysl.cli;

import br.unb.cic.rvsec.crysl.core.CorpusReadError;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationMismatch;
import br.unb.cic.rvsec.crysl.core.emit.MissingVersionError;
import br.unb.cic.rvsec.crysl.mop.RoundTripGate;
import com.beust.jcommander.JCommander;
import com.beust.jcommander.ParameterException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Entry point of the MOP/CrySL conformance component.
 *
 * <p>Three subcommands, described in {@link CompareArgs}, {@link LowerArgs} and
 * {@link CalibrateArgs}. Why the class lives in this module rather than in {@code -mop} or in a
 * fourth {@code -cli} module is recorded in this package's {@code package-info}.
 *
 * <p>{@link #main} is a two-line wrapper over {@link #run}, which returns an {@link ExitCode} and
 * never calls {@code System.exit}. That separation is what makes the exit-code contract testable:
 * a mapping from failure to exit code that only exists inside {@code main} is a mapping nothing can
 * check, and this component's whole subject is claims that nothing checks.
 */
public final class ConformanceCli {

    static final String COMPARE = "compare";
    static final String LOWER = "lower";
    static final String CALIBRATE = "calibrate";

    private static final String PROGRAM = "rvsec-conformance";

    private ConformanceCli() {
    }

    public static void main(String[] args) {
        System.exit(run(args, System.out, System.err).code());
    }

    /**
     * Parses, dispatches and maps whatever comes back to an exit code.
     *
     * @param args the command line
     * @param out  where a subcommand writes what it produced
     * @param err  where a refusal explains itself
     * @return the code {@link #main} hands to {@code System.exit}
     */
    public static ExitCode run(String[] args, PrintStream out, PrintStream err) {
        CompareArgs compare = new CompareArgs();
        LowerArgs lower = new LowerArgs();
        CalibrateArgs calibrate = new CalibrateArgs();

        JCommander jc = JCommander.newBuilder()
                .programName(PROGRAM)
                .addCommand(COMPARE, compare)
                .addCommand(LOWER, lower)
                .addCommand(CALIBRATE, calibrate)
                .build();

        try {
            jc.parse(args);
        } catch (ParameterException e) {
            err.println(e.getMessage());
            err.println(usage(jc));
            return ExitCode.USAGE;
        }

        String command = jc.getParsedCommand();
        if (command == null) {
            err.println("no subcommand given; one of " + COMPARE + ", " + LOWER + ", " + CALIBRATE
                    + " is required");
            err.println(usage(jc));
            return ExitCode.USAGE;
        }

        try {
            switch (command) {
                case COMPARE -> runCompare(compare, out);
                case LOWER -> runLower(lower, out);
                case CALIBRATE -> runCalibrate(calibrate, out);
                default -> throw new IllegalStateException("unreachable: JCommander accepted the "
                        + "unknown subcommand " + command);
            }
            return ExitCode.OK;
        } catch (CorpusReadError e) {
            // Fatal before any metric runs, and nothing partial has been emitted.
            err.println(e.getMessage());
            return ExitCode.CORPUS_READ_ERROR;
        } catch (MissingVersionError e) {
            // A model reached emission unstamped. INV-CONF-01: an unstamped number cannot be
            // attributed to a corpus state, so it is not published at all.
            err.println(e.getMessage());
            return ExitCode.MISSING_VERSION;
        } catch (CalibrationMismatch e) {
            // INV-CONF-14. The whole report has already been printed on `out`, mismatches and
            // passes alike, so this stream carries the finding and not the run's only account of
            // itself. The response is to measure both sides and adjudicate in writing; adjusting
            // the component until the numbers agree would turn this red into a green that is
            // evidence of nothing.
            err.println(e.getMessage());
            return ExitCode.CALIBRATION_MISMATCH;
        }
        // Deliberately not caught here: LiftFailure and Unknown. A .crysl or .mop file that does not
        // lift is a finding about that file - the two upstream residuals, OAEPParameterSpec and
        // SSLEngine, are expected - and an Unknown is a metric declining to guess. Both are counted
        // in the report and both leave the exit code at OK. Turning either into a non-zero exit
        // would make every run of the real corpus red, and the pressure would then be to stop
        // reporting them.
    }

    /**
     * {@code compare}: M0–M4 over one {@code .mop} corpus against the single upstream oracle.
     *
     * <p>The inputs are checked first, so a mistyped path is a {@code CorpusReadError} rather than a
     * corpus in which every specification mysteriously refused.
     *
     * <p>{@link CompareRun} does the work: it builds the two {@code Version} stamps from
     * {@code --corpus}/{@code --commit} and {@code --oracle-commit}, lifts the {@code .mop} side
     * with {@code MopLifter} and the rules with {@code CryslLifter.liftCorpus} keeping each
     * {@code LiftFailure} as a counted finding, indexes {@code --android-jar} with
     * {@code ApiIndex}, loads {@code --alphabet}, pairs specifications with rules <em>by declared
     * type</em> and never by file name (INV-CONF-11), runs M0 first through {@code Pipeline} so
     * that a refused specification never receives an M1–M4 verdict (INV-CONF-09), and writes JSON,
     * CSV and Markdown through the emitters in {@code core.emit} — every table carrying the two
     * stamps and its counting rule.
     *
     * <p>What is printed here is the account of the run, not its findings: the counts that let a
     * reader see something was measured, and where each file went. The findings are in the files.
     */
    private static void runCompare(CompareArgs args, PrintStream out) {
        Path mopDir = requireDirectory(args.mopDir, "the .mop corpus");
        Path rulesDir = requireDirectory(args.rulesDir, "the upstream CrySL-Rules oracle");
        Path alphabet = requireFile(args.alphabetMap, "the order alphabet map");
        Path androidJar = requireFile(args.androidJar, "android.jar");

        out.println("compare: " + args.corpus + " at " + args.commit + " (" + mopDir + ")");
        out.println("oracle:  " + CompareRun.ORACLE_CORPUS + " at " + args.oracleCommit + " ("
                + rulesDir + ")");
        out.println("index:   " + androidJar + "; alphabet: " + alphabet);

        CompareRun.Summary summary = CompareRun.run(args, mopDir, rulesDir, alphabet, androidJar);

        out.println("specifications: " + summary.specifications() + " lifted, "
                + summary.liftFailures() + " did not lift");
        out.println("rules:          " + summary.rules() + " lifted, " + summary.ruleFailures()
                + " did not lift");
        out.println("pairing:        " + summary.pairs() + " pairs, by declared type");
        out.println("vitality:       " + summary.refused() + " refused by M0, "
                + summary.compared() + " paired specifications received M1-M4");
        for (Path file : summary.written()) {
            out.println("wrote " + file);
        }
    }

    /**
     * {@code lower}: {@code mop.lower} followed by the round-trip gate.
     *
     * <p>{@link LowerRun} lifts each file under {@code --mop-dir}, lowers it into {@code --out} and
     * runs the gate over what came out. Layer 1 — the non-normalized AST check over the regenerated
     * file — is what decides; the round trip is printed beside it as a separate answer, because
     * "the emitter lost a field" and "the emitter wrote something unsound" are different findings
     * and folding them together loses both.
     *
     * <p>Layer 2 does not run: the product search needs the paired rule's language and
     * {@link LowerArgs} declares no {@code --rules-dir}. The line below says so, and the gate's own
     * notes say so in each report.
     */
    private static void runLower(LowerArgs args, PrintStream out) {
        Path mopDir = requireDirectory(args.mopDir, "the .mop corpus");

        out.println("lower: " + args.corpus + " at " + args.commit + " (" + mopDir + ")");

        LowerRun.Summary summary = LowerRun.run(args, mopDir);

        out.println("gate: " + summary.passed() + " of " + summary.reports().size()
                + " generations pass Layer 1, " + summary.faithful()
                + " round-trip unchanged; Layer 2 did not run because no rule was supplied");
        for (RoundTripGate.Report report : summary.reports()) {
            out.println(report.specification() + ": "
                    + (report.passed() ? "layer 1 clean" : report.layer1().size() + " violations")
                    + ", " + (report.faithful()
                            ? "round trip faithful"
                            : report.roundTrip().size() + " fields changed")
                    + " -> " + report.generated());
            report.layer1().forEach(violation -> out.println("    layer 1: " + violation));
            report.roundTrip().forEach(change -> out.println("    round trip: " + change));
        }
        summary.liftFailures().forEach(failure -> out.println("did not lift: " + failure));
        summary.lowerFailures().forEach(failure -> out.println("did not lower: " + failure));
    }

    /**
     * {@code calibrate}: the eight quantities measured by the component and checked against the
     * independent route that produced each target.
     *
     * <p>{@link CalibrateRun} lifts the five {@code .mop} corpora and the upstream oracle, pairs
     * through {@code SpecRulePairing}, and answers each of the eight with the rule it counted
     * under. {@code CalibrationGate.check} then compares and reports; it never reconciles, and the
     * component is never adjusted to agree (INV-CONF-14).
     *
     * <p>The whole report is printed <em>before</em> the exit code is decided, mismatches and
     * passes alike, because the two facts a reader needs arrive together — this failed, and those
     * still publish. A mismatch stops the affected metric and nothing else (task 12.4); the run
     * then exits {@link ExitCode#CALIBRATION_MISMATCH}, so a CI step can tell a disagreement from a
     * clean gate without parsing the text.
     */
    private static void runCalibrate(CalibrateArgs args, PrintStream out) {
        Path mopRoot = requireDirectory(args.mopRoot, "the directory of the five .mop corpora");
        Path rulesDir = requireDirectory(args.rulesDir, "the upstream CrySL-Rules oracle");
        Path monitor = args.monitor == null
                ? null
                : requireFile(args.monitor, "the regenerated MultiSpec_1RuntimeMonitor.java");

        out.println("calibrate: " + mopRoot + " at " + args.commit);
        out.println("oracle:    " + rulesDir + " at " + args.oracleCommit);

        CalibrateRun.Summary summary = CalibrateRun.run(args, mopRoot, rulesDir, monitor);
        out.println();
        out.println(summary.report().render());
        summary.routeRetake().ifPresent(out::println);

        if (!summary.report().reproduced()) {
            throw new CalibrationMismatch(summary.report());
        }
    }

    /**
     * The usage text, as a string rather than written by JCommander itself.
     *
     * <p>{@code JCommander.usage()} writes to its own console, which is {@code System.out} and not
     * the stream this class was handed. Routing it through {@code err} keeps every word of a
     * refusal on the stream a caller is reading for refusals.
     */
    private static String usage(JCommander jc) {
        StringBuilder text = new StringBuilder();
        jc.getUsageFormatter().usage(text);
        return text.toString();
    }

    private static Path requireDirectory(String value, String what) {
        Path path = Paths.get(value);
        if (!Files.isDirectory(path) || !Files.isReadable(path)) {
            throw new CorpusReadError(what, path);
        }
        return path;
    }

    private static Path requireFile(String value, String what) {
        Path path = Paths.get(value);
        if (!Files.isRegularFile(path) || !Files.isReadable(path)) {
            throw new CorpusReadError(what, path);
        }
        return path;
    }
}
