package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * A signature the pointcut resolves to is absent from the {@code android.jar} index, so the
 * pointcut can never match on device.
 *
 * <p>This is not the same finding as a dead monitor, and the report keeps them apart: the monitor
 * of {@code HMACParameterSpecSpec} is live and its target class exists in no verified Android API
 * level, which is a defect of the pointcut and not of the monitor.
 *
 * @param signature      the signature that did not resolve
 * @param declaringClass the class named by the pointcut, kept separately because the class may be
 *                       absent as a whole, in which case no signature of it can resolve
 * @param mode           why it did not resolve, in M0's vocabulary, e.g. {@code CLASSE-AUSENTE}
 * @param site           where the pointcut was declared
 */
public record UnresolvedSignature(Signature signature, String declaringClass, String mode,
                                  Provenance site) implements Unknown {

    public UnresolvedSignature {
        Objects.requireNonNull(declaringClass, "UnresolvedSignature.declaringClass is mandatory");
        Objects.requireNonNull(mode, "UnresolvedSignature.mode is mandatory");
        Objects.requireNonNull(site, "UnresolvedSignature.site is mandatory");
    }
}
