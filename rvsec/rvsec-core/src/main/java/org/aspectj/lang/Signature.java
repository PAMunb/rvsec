package org.aspectj.lang;

/**
 * Minimal stand-in for the AspectJ runtime {@code org.aspectj.lang.Signature}
 * interface, shipped in {@code rvsec-core} so the dexlib2-instrumented APK can
 * deliver a {@code Signature} argument to the generated
 * {@code *staticinitEvent(Signature)} monitor methods WITHOUT pulling in the
 * full {@code aspectjrt} jar.
 *
 * <p>The JavaMOP-compiled staticinit advice body calls
 * {@code thisJoinPoint.getStaticPart().getSignature()} and passes the result
 * to the monitor. The generated {@code RuntimeMonitor} consumes the result by
 * calling {@link #getDeclaringType()} and then reflecting on the returned
 * {@code Class} (see {@code MultiSpec_1RuntimeMonitor.java:1524}). Only
 * {@code getDeclaringType()} is exercised at runtime; the remaining six methods
 * exist so {@link ClassSignature} structurally satisfies this interface and so
 * any future consumer that touches them gets a coherent (non-null) value.
 */
public interface Signature {

    String toString();

    String toShortString();

    String toLongString();

    String getName();

    int getModifiers();

    Class<?> getDeclaringType();

    String getDeclaringTypeName();
}
