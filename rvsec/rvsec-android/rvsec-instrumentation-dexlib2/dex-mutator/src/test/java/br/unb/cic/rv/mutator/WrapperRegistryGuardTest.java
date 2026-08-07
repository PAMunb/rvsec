package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.WrapperEmitter;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The wrapper registry refuses to rebind a key to a different wrapper
 * (gh100 task 5.3, D-B1).
 *
 * <p>The registry maps the original call site's signature to the wrapper that
 * replaces it. Two entries sharing that signature used to overwrite silently,
 * so the second advice's wrapper won and the first advice's monitor events
 * stopped firing at the site — while the weave reported success and the
 * counters reported the wrapper as generated.
 *
 * <p>{@code WrapperEmitter} now merges every advice over a call into one
 * wrapper, so this guard should never fire in practice. That is what makes it
 * worth asserting: it is the invariant that says the emitter and the registry
 * still agree about what counts as the same call, and a silent overwrite is
 * precisely how their disagreement stayed invisible.
 */
class WrapperRegistryGuardTest {

    private static WrapperEmitter.WrapperEntry entry(String wrapperName) {
        return new WrapperEmitter.WrapperEntry(
                wrapperName, "java.security.SecureRandom", "getInstance",
                List.of("java.lang.String"), "java.security.SecureRandom",
                /*isStatic=*/ true);
    }

    private static DexWeaver weaverWith(WrapperEmitter.WrapperEntry... entries) {
        return new DexWeaver(new EmitterDispatch(), new RegisterAllocator(), List.of(entries));
    }

    @Test
    void twoWrappersForOneOriginalCallFailLoud() {
        // Both entries describe the same original call, so both compute the
        // same registry key — the shape WrapperEmitter used to emit before the
        // merge, and the shape whose second entry used to win silently.
        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> weaverWith(entry("java_security_SecureRandom_getInstance"),
                                 entry("java_security_SecureRandom_getInstance_1")));

        assertTrue(error.getMessage().contains("java_security_SecureRandom_getInstance_1"),
                "the message must name the wrapper that would have overwritten, so the "
                        + "emitter/registry disagreement is diagnosable: " + error.getMessage());
    }

    @Test
    void registeringTheSameWrapperTwiceIsNotARebinding() {
        // Identical entries bind the key to the same reference. That is a
        // duplicate, not a conflict, and failing on it would turn a harmless
        // repetition into a build failure.
        assertDoesNotThrow(() -> weaverWith(
                entry("java_security_SecureRandom_getInstance"),
                entry("java_security_SecureRandom_getInstance")));
    }

    @Test
    void wrappersForDifferentCallsCoexist() {
        // The control: the guard must reject rebinding, not registration.
        WrapperEmitter.WrapperEntry digest = new WrapperEmitter.WrapperEntry(
                "java_security_MessageDigest_getInstance", "java.security.MessageDigest",
                "getInstance", List.of("java.lang.String"), "java.security.MessageDigest",
                /*isStatic=*/ true);

        assertDoesNotThrow(() -> weaverWith(
                entry("java_security_SecureRandom_getInstance"), digest));
    }
}
