package br.unb.cic.rvsec.crysl.crysl;

import br.unb.cic.rvsec.crysl.core.ParseError;
import com.google.inject.Injector;
import de.darmstadt.tu.crossing.CrySLStandaloneSetup;
import de.darmstadt.tu.crossing.crySL.Aggregate;
import de.darmstadt.tu.crossing.crySL.Domainmodel;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.xtext.nodemodel.ICompositeNode;
import org.eclipse.xtext.nodemodel.util.NodeModelUtils;
import org.eclipse.xtext.resource.XtextResource;
import org.eclipse.xtext.resource.XtextResourceSet;

/**
 * What the CrySL façade cannot answer, read from the EMF abstract syntax tree: whether the parse
 * was clean, where each section and each declaration sits in the file, and what the rule calls its
 * events and aggregates.
 *
 * <p><strong>This route names and locates; it never computes.</strong> D-19 draws the boundary and
 * it is a boundary, not a preference. The comparison runs entirely on the façade, because the
 * façade supplies exactly what the comparison needs — {@code CrySLMethod} gives declaring type,
 * method name and parameter types, which is the {@code Signature} alphabet the two sides share. The
 * three things the façade does <em>not</em> expose are the three things only this route provides:
 *
 * <ul>
 *   <li><strong>Validity.</strong> {@code CrySLModelReader} recovers from errors and then refuses
 *       the rule with one opaque message; only {@code XtextResource.getErrors()} says what was
 *       wrong and on which line.
 *   <li><strong>Positions.</strong> There is no position API anywhere in {@code crysl.rule.*}.
 *       {@code NodeModelUtils} is the only source of {@code file:line}.
 *   <li><strong>Names.</strong> {@code TransitionEdge.getLabel()} answers
 *       {@code Collection<CrySLMethod>} — method signatures, not the {@code Gets}/{@code Inits}
 *       labels the rule was written with.
 * </ul>
 *
 * <p>The names in {@link #eventNames()} are for reports and for a human reading a finding. They are
 * <strong>not</strong> part of the comparison alphabet and no metric may key on them: {@code order}
 * is an automaton over {@code Signature} and never over a label (INV-CONF-03). Pulling CrySL event
 * names into the alphabet would reopen the non-disjointness problem at a second level, which is
 * exactly the alternative D-19 rejected.
 *
 * @param file       the rule this provenance describes
 * @param errors     the diagnostics the resource reported, in resource order; empty means clean
 * @param eventNames the {@code EVENTS} declarations in file order, with their kind and line
 * @param objectLines line of each {@code OBJECTS} declaration, keyed by the declared name
 * @param sectionLines line of each section present in the file, measured at its <em>first
 *                     element</em> rather than at the section keyword — the grammar attaches the
 *                     keyword to the enclosing rule, so a block's node begins one line below it
 */
public record CryslProvenance(Path file, List<ParseError> errors, List<EventName> eventNames,
                              Map<String, Integer> objectLines, Map<Section, Integer> sectionLines) {

    /** The sections of a CrySL rule this route locates. */
    public enum Section { SPEC, OBJECTS, FORBIDDEN, EVENTS, ORDER, CONSTRAINTS, REQUIRES, ENSURES, NEGATES }

    /** Whether a declaration is a single labelled method call or an aggregate of other events. */
    public enum EventKind { LABELED, AGGREGATE }

    /**
     * One {@code EVENTS} declaration, as the rule names it.
     *
     * @param name the declared name, e.g. {@code i1} or {@code Inits}
     * @param kind labelled call or aggregate
     * @param line 1-based line of the declaration
     */
    public record EventName(String name, EventKind kind, int line) {
        public EventName {
            Objects.requireNonNull(name, "EventName.name is mandatory");
            Objects.requireNonNull(kind, "EventName.kind is mandatory");
        }
    }

    public CryslProvenance {
        Objects.requireNonNull(file, "CryslProvenance.file is mandatory");
        errors = List.copyOf(errors);
        eventNames = List.copyOf(eventNames);
        objectLines = Map.copyOf(objectLines);
        sectionLines = Map.copyOf(sectionLines);
    }

    /** True when the resource loaded with no diagnostic at all. */
    public boolean valid() {
        return errors.isEmpty();
    }

    /**
     * The line a section's first element sits on, when the file declares that section.
     *
     * <p>Callers use it as the fallback position for an item the façade hands over without one: a
     * constraint clause belongs to its {@code CONSTRAINTS} block even when nothing can say which
     * line of it the clause occupies.
     *
     * <p>It is the first element's line, not the keyword's. In {@code KeyGenerator.crysl} the
     * {@code ORDER} keyword is on line 25 and this answers 26, because the grammar attaches the
     * keyword to the enclosing rule and the block's node starts at its content.
     */
    public Optional<Integer> lineOf(Section section) {
        return Optional.ofNullable(sectionLines.get(section));
    }

    /**
     * The Guice injector Xtext needs, built once for the JVM.
     *
     * <p>Sharing the injector is safe and sharing a {@code CrySLModelReader} is not, and the
     * difference is not a matter of degree. The reader accumulates {@code OBJECTS} scope across the
     * rules it reads, so the set of rules that load becomes a function of read order (INV-CONF-04).
     * The injector holds grammar services — a parser, a linker, a value converter — that carry no
     * per-rule state. What must not be shared is the {@link XtextResourceSet}: a resource set caches
     * loaded resources and resolves cross-references between them, which would leak scope in exactly
     * the way the fresh reader exists to prevent. One resource set per file, below.
     */
    private static final class InjectorHolder {
        private static final Injector INSTANCE =
                new CrySLStandaloneSetup().createInjectorAndDoEMFRegistration();

        private InjectorHolder() {
        }
    }

    /**
     * Reads the EMF tree of one rule.
     *
     * <p>Never throws on a rule that does not parse: a file with errors still yields a provenance,
     * carrying those errors. That is the point — the caller needs the diagnostics precisely in the
     * case where the façade refused the rule.
     *
     * @param cryslRule the rule file
     * @return its provenance, with {@link #valid()} false when the resource reported diagnostics
     */
    public static CryslProvenance read(Path cryslRule) {
        Objects.requireNonNull(cryslRule, "cryslRule is mandatory");
        XtextResourceSet resourceSet = InjectorHolder.INSTANCE.getInstance(XtextResourceSet.class);
        resourceSet.addLoadOption(XtextResource.OPTION_RESOLVE_ALL, Boolean.TRUE);
        Resource resource = resourceSet.getResource(
                URI.createFileURI(cryslRule.toAbsolutePath().toString()), true);

        List<ParseError> errors = new ArrayList<>();
        for (Resource.Diagnostic diagnostic : resource.getErrors()) {
            errors.add(new ParseError(Math.max(diagnostic.getLine(), 0), diagnostic.getMessage()));
        }

        List<EventName> eventNames = new ArrayList<>();
        Map<String, Integer> objectLines = new LinkedHashMap<>();
        Map<Section, Integer> sectionLines = new EnumMap<>(Section.class);

        if (!resource.getContents().isEmpty()
                && resource.getContents().get(0) instanceof Domainmodel model) {
            lineOf(model).ifPresent(line -> sectionLines.put(Section.SPEC, line));
            collect(model, eventNames, objectLines, sectionLines);
        }
        return new CryslProvenance(cryslRule, errors, eventNames, objectLines, sectionLines);
    }

    private static void collect(Domainmodel model, List<EventName> eventNames,
                                Map<String, Integer> objectLines, Map<Section, Integer> sectionLines) {
        if (model.getObjects() != null) {
            lineOf(model.getObjects()).ifPresent(line -> sectionLines.put(Section.OBJECTS, line));
            for (de.darmstadt.tu.crossing.crySL.Object declaration : model.getObjects().getDeclarations()) {
                // A rule that uses a reserved word as an object name parses that declaration into a
                // nameless node - OAEPParameterSpec.crysl:8 is the corpus witness. Skipping it here
                // keeps the provenance readable; the defect is reported through the diagnostics.
                if (declaration.getName() != null) {
                    objectLines.put(declaration.getName(), lineOf(declaration).orElse(0));
                }
            }
        }
        if (model.getForbidden() != null) {
            lineOf(model.getForbidden()).ifPresent(line -> sectionLines.put(Section.FORBIDDEN, line));
        }
        if (model.getEvents() != null) {
            lineOf(model.getEvents()).ifPresent(line -> sectionLines.put(Section.EVENTS, line));
            for (de.darmstadt.tu.crossing.crySL.Event event : model.getEvents().getEvents()) {
                if (event.getName() != null) {
                    EventKind kind = event instanceof Aggregate ? EventKind.AGGREGATE : EventKind.LABELED;
                    eventNames.add(new EventName(event.getName(), kind, lineOf(event).orElse(0)));
                }
            }
        }
        if (model.getOrder() != null) {
            lineOf(model.getOrder()).ifPresent(line -> sectionLines.put(Section.ORDER, line));
        }
        if (model.getConstraints() != null) {
            lineOf(model.getConstraints()).ifPresent(line -> sectionLines.put(Section.CONSTRAINTS, line));
        }
        if (model.getRequires() != null) {
            lineOf(model.getRequires()).ifPresent(line -> sectionLines.put(Section.REQUIRES, line));
        }
        if (model.getEnsures() != null) {
            lineOf(model.getEnsures()).ifPresent(line -> sectionLines.put(Section.ENSURES, line));
        }
        if (model.getNegates() != null) {
            lineOf(model.getNegates()).ifPresent(line -> sectionLines.put(Section.NEGATES, line));
        }
    }

    private static Optional<Integer> lineOf(EObject node) {
        ICompositeNode composite = NodeModelUtils.getNode(node);
        return composite == null ? Optional.empty() : Optional.of(composite.getStartLine());
    }
}
