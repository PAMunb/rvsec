package br.unb.cic.rv.pointcut;

/**
 * Thrown when a {@code BaseAspect.notwithin()} reference is encountered but the active aspect's
 * {@code baseAspectExclusions} list is empty — i.e. a legacy descriptor produced by a JavaMOP build
 * pre-dating the canonical twelve-entry exclusion expansion. Fail-closed (G-decision): the closure
 * surfaces such descriptors at weave time rather than silently weaving without the exclusion filter.
 */
public class LegacyDescriptorException extends RuntimeException {

    private final String aspectName;

    public LegacyDescriptorException(String aspectName) {
        super("aspect '" + aspectName + "' references BaseAspect.notwithin() but its "
                + "baseAspectExclusions list is empty — legacy descriptor (pre-dating the canonical "
                + "exclusion expansion); regenerate via the current JavaMOP toolchain");
        this.aspectName = aspectName;
    }

    public String aspectName() {
        return aspectName;
    }
}
