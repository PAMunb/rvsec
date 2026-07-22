package org.aspectj.lang;

/**
 * The single {@link Signature} implementation the dexlib2 weaver instantiates
 * at a synthesized (or existing) {@code <clinit>} to satisfy
 * {@code *staticinitEvent(Signature)}.
 *
 * <p>The weaver emits, at the class initializer of the matched type {@code T}:
 * <pre>
 *   const-class   vC, T
 *   new-instance  vS, Lorg/aspectj/lang/ClassSignature;
 *   invoke-direct {vS, vC}, ClassSignature.&lt;init&gt;(Ljava/lang/Class;)V
 *   invoke-static {vS}, mop....staticinitEvent(Lorg/aspectj/lang/Signature;)V
 * </pre>
 * so {@code declaringType} is exactly {@code T.class} (the live class, not its
 * name) — required because the monitor body does
 * {@code Class k = sig.getDeclaringType(); k.getDeclaredMethod(...)}.
 *
 * <p>The other accessors are derived from {@code declaringType}: there is no
 * member-level join point at a static initializer, so {@code getName()} reports
 * the class name and {@code getModifiers()} reports {@code 0}.
 */
public final class ClassSignature implements Signature {

    private final Class<?> declaringType;

    public ClassSignature(Class<?> declaringType) {
        this.declaringType = declaringType;
    }

    @Override
    public Class<?> getDeclaringType() {
        return declaringType;
    }

    @Override
    public String getDeclaringTypeName() {
        return declaringType == null ? "" : declaringType.getName();
    }

    @Override
    public String getName() {
        return declaringType == null ? "" : declaringType.getName();
    }

    @Override
    public int getModifiers() {
        return 0;
    }

    @Override
    public String toString() {
        return getName();
    }

    @Override
    public String toShortString() {
        return getName();
    }

    @Override
    public String toLongString() {
        return getName();
    }
}
