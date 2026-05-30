package br.unb.cic.rv.pointcut;

/**
 * Thrown when a {@link NamedRefPC} carries a name the matcher cannot resolve to a concrete pointcut
 * (G-decision fail-closed: replaces the round-7 always-match-with-WARN trap). The only resolvable
 * named references are {@code BaseAspect.notwithin()} (expanded against
 * {@code AspectDescriptor.baseAspectExclusions}) and the vacuously-true {@code adviceexecution()}
 * family. Any other name surfaces here at weave time rather than silently matching everything.
 */
public class UnresolvedNamedRefException extends RuntimeException {

    private final String aspectName;
    private final String unresolvedName;

    public UnresolvedNamedRefException(String aspectName, String unresolvedName) {
        super("unresolved named pointcut reference '" + unresolvedName + "' in aspect '"
                + aspectName + "' — only BaseAspect.notwithin() and adviceexecution() are resolvable");
        this.aspectName = aspectName;
        this.unresolvedName = unresolvedName;
    }

    public String aspectName() {
        return aspectName;
    }

    public String unresolvedName() {
        return unresolvedName;
    }
}
