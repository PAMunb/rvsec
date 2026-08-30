package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.io.File;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Two shape properties of the lift that a comment cannot enforce.
 *
 * <p>The first is the absence of a batch entry point. {@code JavaMOPParser} keeps its parser in a
 * {@code private static} field and {@code MOPNameSpace} is a static map, so the parse is not
 * parallelisable — and the way that rule gets broken is not by someone spawning threads on purpose,
 * it is by a convenience overload taking a directory and a later reader writing
 * {@code .parallelStream()} over it because the signature invites it. Asserting the API shape is
 * what keeps the invitation from existing.
 *
 * <p>The second is that the pointcut expansion actually produces the overlapping alphabet the whole
 * order comparison is designed around (D-02). Without the expansion the overlap is invisible until
 * something tries to compare the two sides, and by then it looks like a bug in the comparator.
 */
class LiftApiShapeTest {

    @Test
    @DisplayName("MopLifter offers no batch overload for a parallelStream to latch onto")
    void test_no_batch_entry_point() {
        for (Method method : MopLifter.class.getDeclaredMethods()) {
            if (!Modifier.isPublic(method.getModifiers())) {
                continue;
            }
            for (Class<?> parameter : method.getParameterTypes()) {
                if (parameter.equals(Path.class)) {
                    // Path is itself an Iterable<Path> - of its own name elements, not of files -
                    // so it has to be named before the Iterable check, or the one signature the
                    // lifter is supposed to have would be the one this test rejects.
                    continue;
                }
                assertFalse(Collection.class.isAssignableFrom(parameter)
                                || Stream.class.isAssignableFrom(parameter)
                                || Iterable.class.isAssignableFrom(parameter)
                                || parameter.isArray()
                                || parameter.equals(File.class),
                        "MopLifter." + method.getName() + " takes " + parameter.getSimpleName()
                                + "; the lifter takes one path at a time, because the parser holds "
                                + "state in a static field and a batch signature is how a caller "
                                + "ends up parallelising it");
            }
            assertTrue(Arrays.asList(method.getParameterTypes()).contains(Path.class)
                            || method.getParameterCount() == 0,
                    "MopLifter." + method.getName() + " should take the single Path it lifts");
        }
    }

    @Test
    @DisplayName("the expanded alphabet is non-disjoint, which is what D-02 is about")
    void test_alphabet_is_not_disjoint() throws LiftFailure {
        MopLifter lifter = new MopLifter();

        // jca/MacSpec.mop declares g1 and g3 over the same Mac.getInstance(String), separated only
        // by a condition: g1 fires on a safe algorithm, g3 on an unsafe one. One call, two labels.
        MopLift mac = lifter.read(Corpora.file("jca", "MacSpec.mop"), Corpora.version("jca"));
        Set<Signature> shared = sharedSignatures(mac, "g1", "g3");
        assertEquals(1, shared.size(), "g1 and g3 match exactly one signature in common");
        Signature signature = shared.iterator().next();
        assertEquals("javax.crypto.Mac", signature.declaringType());
        assertEquals("getInstance", signature.name());
        assertEquals(List.of("java.lang.String"), signature.paramTypes(),
                "the file writes 'String' and imports no java.lang; the expander applies the "
                        + "implicit import every compilation unit has, so the parameter type is "
                        + "qualified here and matches the android.jar index, which spells every "
                        + "type fully");

        // The four-way case, where the guard is what separates the labels and there are three
        // guarded alternatives against one unguarded: PBEKeySpecSpec's c1 and its three err labels
        // all match one PBEKeySpec constructor.
        MopLift pbe = lifter.read(Corpora.file("jca", "PBEKeySpecSpec.mop"), Corpora.version("jca"));
        assertFalse(sharedSignatures(pbe, "c1", "err1").isEmpty());
        assertFalse(sharedSignatures(pbe, "err1", "err3").isEmpty());
    }

    @Test
    @DisplayName("a pointcut with alternatives expands to every signature it names")
    void test_alternatives_expand() throws LiftFailure {
        MopLifter lifter = new MopLifter();
        MopLift mac = lifter.read(Corpora.file("jca", "MacSpec.mop"), Corpora.version("jca"));

        // event f1: (call(byte[] Mac.doFinal(byte[])) || call(byte[] Mac.doFinal())) - one event,
        // two signatures. The return type comes from the method pattern (trap g): getRetType() is
        // null for every event of all 239 files.
        Event f1 = eventOf(mac, "f1");
        assertEquals(2, f1.signatures().size());
        assertTrue(f1.signatures().stream().allMatch(s -> s.returnType().equals("byte[]")),
                "the declared return type is read from MethodPattern.getType()");
        assertTrue(f1.signatures().stream().anyMatch(s -> s.paramTypes().isEmpty()));
        assertTrue(f1.signatures().stream().anyMatch(s -> s.paramTypes().equals(List.of("byte[]"))));
    }

    private static Set<Signature> sharedSignatures(MopLift lift, String left, String right) {
        Set<Signature> shared = new LinkedHashSet<>(eventOf(lift, left).signatures());
        shared.retainAll(eventOf(lift, right).signatures());
        return shared;
    }

    private static Event eventOf(MopLift lift, String label) {
        return lift.model().events().stream()
                .filter(e -> e.label().name().equals(label))
                .findFirst()
                .orElseThrow(() -> new AssertionError("no event " + label));
    }
}
