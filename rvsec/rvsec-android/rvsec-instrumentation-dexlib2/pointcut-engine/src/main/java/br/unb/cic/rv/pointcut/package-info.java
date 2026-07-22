/**
 * Pointcut parsing, type resolution, and Android API indexing.
 *
 * <p>Scope (per design D1, §Module dependency direction):
 * <ul>
 *   <li>Consumes the POJO model from {@code br.unb.cic.rv.descriptor} — specifically
 *       the {@code expression} and {@code imports} strings emitted by patched JavaMOP.</li>
 *   <li>Produces a typed {@link br.unb.cic.rv.pointcut.PointcutExpression} AST
 *       consumed by {@code advice-emitter} when planning injection.</li>
 *   <li>Hosts {@link br.unb.cic.rv.pointcut.PointcutMatcher}, which performs the
 *       DEX-level matching: it takes dexlib2
 *       {@code ClassDef}/{@code Method}/{@code Instruction} plus the AST produced
 *       here.</li>
 * </ul>
 *
 * <p>Position enum and PointcutExpression AST types deliberately live here (not in
 * descriptor-reader) because descriptor-reader is a pure-POJO module with no parser
 * dependency.
 */
package br.unb.cic.rv.pointcut;
