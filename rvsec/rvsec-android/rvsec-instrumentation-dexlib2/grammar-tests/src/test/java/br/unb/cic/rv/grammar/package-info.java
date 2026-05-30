/**
 * Executable oracle for {@code docs/aspectj_grammar_coverage.md} (the AspectJ grammar coverage
 * matrix). Each matrix row has exactly one backing test method in this package tree; tests are kept
 * in 1:1 correspondence with matrix rows and {@code MatrixIntegrityTest} breaks the build if either
 * side moves alone.
 *
 * <p><b>Zero {@code @Disabled} annotations</b> remain post round-8: every row has an enabled passing
 * test. COVERED tests assert post-fix behaviour; EXPLICIT-NO-OP tests assert
 * {@link java.lang.UnsupportedOperationException}; NOT-NEEDED α tests assert
 * {@code DemandCounter.countMop == 0}; NOT-NEEDED β tests assert {@code DemandCounter.countCompiledAj == 0}
 * plus the named upstream absorber ({@link br.unb.cic.rv.grammar.util.AbsorbingStage}) and an
 * empirical-evidence anchor.
 *
 * <p>The {@code util} subpackage holds the matrix infrastructure: {@code DemandCounter} (portable
 * demand counter), {@code MatrixMarkdownParser} (commonmark table parser), {@code AspectJDesignators}
 * (the closed enumeration), and {@code AbsorbingStage} (the recognised upstream absorbers).
 */
package br.unb.cic.rv.grammar;
