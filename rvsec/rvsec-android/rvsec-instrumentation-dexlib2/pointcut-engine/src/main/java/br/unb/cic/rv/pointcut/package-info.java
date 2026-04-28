/**
 * Pointcut parsing, type resolution, and Android API indexing.
 *
 * <p>Scope (per design D1, §Module dependency direction):
 * <ul>
 *   <li>Consumes the POJO model from {@code br.unb.cic.rv.descriptor} — specifically
 *       the {@code expression} and {@code imports} strings emitted by patched JavaMOP.</li>
 *   <li>Produces a typed {@link br.unb.cic.rv.pointcut.PointcutExpression} AST
 *       consumed by {@code advice-emitter} when planning injection.</li>
 *   <li>Does not touch dexlib2: the actual DEX-level matching happens in
 *       {@code pointcut-engine.PointcutMatcher} (task 3.6) which this module
 *       will host; it takes dexlib2 {@code ClassDef}/{@code Method}/{@code Instruction}
 *       plus the AST produced here.</li>
 * </ul>
 *
 * <p>Position enum and PointcutExpression AST types deliberately live here (not in
 * descriptor-reader) because descriptor-reader is a pure-POJO module with no parser
 * dependency.
 */
package br.unb.cic.rv.pointcut;
