package br.unb.cic.rvsec.crysl.crysl.cli;

import br.unb.cic.rvsec.crysl.core.CorpusReadError;
import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.mop.LowerFailure;
import br.unb.cic.rvsec.crysl.mop.MopLift;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import br.unb.cic.rvsec.crysl.mop.RoundTripGate;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * The body of {@code lower}: model → {@code .mop} text, then the round-trip gate over what came out.
 *
 * <h2>What decides, and what is only evidence</h2>
 *
 * <p>{@link RoundTripGate.Report#passed()} is Layer 1 and nothing else — the non-normalized AST
 * check over the regenerated file. The round trip is a different question,
 * {@link RoundTripGate.Report#faithful()}: whether the model survived the trip through text
 * unchanged, which is about what the emitter lost and not about whether what it emitted is sound.
 * Both are reported, separately, and neither is folded into the other.
 *
 * <h2>Layer 2 does not run here, and the report says so</h2>
 *
 * <p>The product-search evidence needs the paired rule's language and the API index needs
 * {@code android.jar}; {@link LowerArgs} declares neither, because the lowering group had not fixed
 * that input surface when the arguments were written. So this command runs Layer 1 over every file
 * and passes {@link Optional#empty()} for both, which makes the gate emit its own
 * {@code NO_INDEX_NOTE} into the report's notes. Supplying an empty oracle silently would be the
 * defect; the gate's note is what stops it being silent.
 *
 * <h2>Why the verdicts are printed rather than tabulated</h2>
 *
 * <p>Every table {@code core.emit} publishes carries two stamps, the {@code .mop} corpus and the
 * oracle. {@code lower} has no oracle — there is no {@code --rules-dir} — so a stamped table of its
 * verdicts could only be built by inventing an oracle stamp, which is the exact failure INV-CONF-01
 * exists to prevent. The generated {@code .mop} files go to {@code --out}; the verdicts go to the
 * caller's stream.
 */
final class LowerRun {

    private LowerRun() {
    }

    /**
     * What the run produced.
     *
     * @param reports      one per file that lowered and lifted back
     * @param liftFailures {@code .mop} files of the corpus that did not lift at all
     * @param lowerFailures files that lifted and then failed to lower or to lift back, with the
     *                     reason; findings about the emitter, counted and not fatal
     */
    record Summary(List<RoundTripGate.Report> reports, List<String> liftFailures,
                   List<String> lowerFailures) {

        /** How many generations Layer 1 accepted. */
        long passed() {
            return reports.stream().filter(RoundTripGate.Report::passed).count();
        }

        /** How many models came back from text unchanged. */
        long faithful() {
            return reports.stream().filter(RoundTripGate.Report::faithful).count();
        }
    }

    /**
     * Lowers every specification of the corpus and runs the gate over each.
     *
     * @param args   the parsed {@code lower} arguments
     * @param mopDir the corpus, already checked readable
     * @return the per-file verdicts and the failures
     */
    static Summary run(LowerArgs args, Path mopDir) {
        Version version = new Version(args.corpus,
                new SourceStamp(CompareRun.MOP_REPOSITORY, args.commit, Instant.now()));
        Path outputDir = outputDirectory(args.outputDir);

        MopLifter lifter = new MopLifter();
        List<RoundTripGate.Report> reports = new ArrayList<>();
        List<String> liftFailures = new ArrayList<>();
        List<String> lowerFailures = new ArrayList<>();

        for (Path file : mopFiles(mopDir)) {
            MopLift lift;
            try {
                lift = lifter.read(file, version);
            } catch (LiftFailure e) {
                liftFailures.add(file.getFileName() + ": " + e.getMessage());
                continue;
            }
            try {
                reports.add(RoundTripGate.run(lift, outputDir, Optional.empty(), Optional.empty()));
            } catch (LowerFailure e) {
                lowerFailures.add(e.specification() + ": " + e.getMessage());
            } catch (LiftFailure e) {
                // The generated file did not parse. That is the harshest finding the gate can
                // produce and it is still a finding about the emitter, not a failure of the run.
                lowerFailures.add(file.getFileName() + ": the generated .mop did not lift back - "
                        + e.getMessage());
            } catch (IOException e) {
                throw new UncheckedIOException("could not write the lowered specification of "
                        + file.getFileName() + " under " + outputDir, e);
            }
        }
        return new Summary(reports, liftFailures, lowerFailures);
    }

    private static Path outputDirectory(String value) {
        Path outputDir = Paths.get(value);
        try {
            Files.createDirectories(outputDir);
        } catch (IOException e) {
            throw new UncheckedIOException("could not create the output directory " + outputDir, e);
        }
        return outputDir;
    }

    /**
     * The {@code .mop} files of the corpus, in name order.
     *
     * <p>An empty directory is refused for the same reason {@code compare} refuses one: a run that
     * lowered nothing and exited {@code 0} would report a clean gate over no files.
     */
    private static List<Path> mopFiles(Path mopDir) {
        try (Stream<Path> entries = Files.list(mopDir)) {
            List<Path> files = entries
                    .filter(path -> path.getFileName().toString().endsWith(".mop"))
                    .sorted()
                    .toList();
            if (files.isEmpty()) {
                throw new CorpusReadError(
                        "a .mop corpus with at least one specification in it (this directory holds "
                                + "no *.mop file, and a gate that ran over no file would report a "
                                + "clean pass and exit 0)", mopDir);
            }
            return files;
        } catch (IOException e) {
            throw new CorpusReadError("the .mop corpus (" + e.getMessage() + ")", mopDir);
        }
    }
}
