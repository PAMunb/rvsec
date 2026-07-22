/**
 * Compiles generated monitor / wrapper / Coverage Java sources to
 * {@code .class} (via {@code javac}) and then to DEX (via Android SDK
 * {@code d8}).
 *
 * <p>This module owns the subprocess plumbing for source → bytecode →
 * DEX and the canonical source of the {@code mop.Coverage} runtime class
 * (INV-INS-60: thread-safe {@code ConcurrentHashMap.newKeySet()} backing
 * store).
 *
 * <p>Spec-set agnostic: compiles monitor sources regardless of whether the
 * source specifications were JCA or Generic — rv-monitor generates a
 * {@code MultiSpec_*RuntimeMonitor.java} with identical shape for either set.
 */
package br.unb.cic.rv.builder;
