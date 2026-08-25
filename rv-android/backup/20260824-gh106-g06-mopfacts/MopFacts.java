package br.unb.cic.rvsec.crysl.crysl;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.metric.HandlerState;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.MonitorFacts;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.mop.HandlerBlock;
import br.unb.cic.rvsec.crysl.mop.MopLift;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import javamop.parser.SpecExtractor;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.mopspec.EventDefinition;
import javamop.parser.ast.mopspec.JavaMOPSpec;
import javamop.parser.ast.mopspec.MOPParameters;
import javamop.util.MOPNameSpace;

/**
 * Builds the {@link MonitorFacts} M0 consumes from one {@code .mop} file.
 *
 * <p>This lives in the test tree and it should not stay there. Two of the three parser-derived facts
 * — the handler states and the declared counts — already travel on {@code mop.MopLift}; the third,
 * the parameter binding, does not, and {@code EventDefinition.getMOPParametersOnSpec()} is the only
 * route to it. The lifter module was owned by another task while G06 ran, so this class reaches for
 * the parser itself rather than editing {@code MopLift} underneath its owner. The production wiring
 * belongs on the lift: {@code MopLift} should carry {@code eventsBindingParameters} and hand M0 a
 * {@code MonitorFacts}, and this helper should then be deleted rather than kept as a second route.
 *
 * <p>The corpus is read from the sibling {@code rvsec-mop} module in the working tree and never
 * written (INV-CONF-12), which is the same source {@code mop.Corpora} reads.
 */
final class MopFacts {

    /** The directory holding the five corpus directories, relative to this module. */
    private static final Path CORPORA =
            Paths.get("..", "..", "rvsec-mop", "src", "main", "resources").normalize();

    private MopFacts() {
    }

    /** One {@code .mop} file of a corpus. */
    static Path file(String corpus, String name) {
        return CORPORA.resolve(corpus).resolve(name);
    }

    /** The {@code .mop} files of one corpus, sorted, so that a run is diffable against the last. */
    static List<Path> filesOf(String corpus) {
        try (Stream<Path> entries = Files.list(CORPORA.resolve(corpus))) {
            return entries.filter(p -> p.getFileName().toString().endsWith(".mop")).sorted()
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot list corpus " + corpus, e);
        }
    }

    /**
     * The stamp a lifted model carries in these tests.
     *
     * <p>The commit is a fixed literal rather than the working tree's HEAD: a test asserting
     * reproducible counts must itself be reproducible, and INV-CONF-01 only requires that a model
     * carry the stamp of the corpus it came from.
     */
    static Version version(String corpus) {
        return new Version(corpus, new SourceStamp("rvsec", "working-tree", Instant.EPOCH));
    }

    /** The lift and the facts, from one parse each. */
    record Read(MopLift lift, MonitorFacts facts) {
    }

    /** Lifts one file and assembles the M0 inputs. */
    static Read read(String corpus, String name) throws LiftFailure {
        Path path = file(corpus, name);
        MopLift lift = new MopLifter().read(path, version(corpus));
        return new Read(lift, factsOf(path, lift));
    }

    /** Lifts one file already located. */
    static Read read(String corpus, Path path) throws LiftFailure {
        MopLift lift = new MopLifter().read(path, version(corpus));
        return new Read(lift, factsOf(path, lift));
    }

    private static MonitorFacts factsOf(Path path, MopLift lift) {
        Map<String, HandlerState> handlers = new LinkedHashMap<>();
        for (Map.Entry<String, HandlerBlock> entry : lift.handlers().entrySet()) {
            handlers.put(entry.getKey(), stateOf(entry.getValue().status()));
        }
        return new MonitorFacts(lift.declaredParameterCount(), lift.declaredEventCount(),
                eventsBindingParameters(path), handlers, MisuseAbsorption.scan(path),
                lift.site());
    }

    private static HandlerState stateOf(HandlerBlock.Status status) {
        return switch (status) {
            case ABSENT -> HandlerState.ABSENT;
            case EMPTY -> HandlerState.EMPTY;
            case NON_EMPTY -> HandlerState.NON_EMPTY;
            case UNPARSED -> HandlerState.UNPARSED;
        };
    }

    /**
     * How many events bind at least one declared specification parameter.
     *
     * <p>{@code getMOPParametersOnSpec()} is the intersection JavaMOP itself computes between an
     * event's parameters and the specification's, and it is what decides whether the generated
     * monitor indexes: with the intersection empty for every event, the monitor has nothing to key
     * a slice on and compiles to one monitor for the whole program.
     */
    private static int eventsBindingParameters(Path path) {
        MOPNameSpace.init();
        MOPSpecFile specFile;
        try {
            specFile = SpecExtractor.parse(new File(path.toString()));
        } catch (Exception e) {
            throw new IllegalStateException("cannot parse " + path, e);
        }
        JavaMOPSpec spec = specFile.getSpecs().get(0);
        if (spec.getEvents() == null) {
            return 0;
        }
        int binding = 0;
        for (EventDefinition event : spec.getEvents()) {
            MOPParameters bound = event.getMOPParametersOnSpec();
            if (bound != null && bound.size() > 0) {
                binding++;
            }
        }
        return binding;
    }
}
