/**
 * The component's command line, and the record of why it lives in this module.
 *
 * <h2>Why here</h2>
 *
 * <p>The CLI is the one place that needs all three modules at once: it lifts {@code .mop} files
 * ({@code -mop}), it reads the upstream rules ({@code -crysl}), and it emits over the shared model
 * ({@code -core}). The three-module shape gives that no natural home, so the choice was between
 * putting the CLI in one of the existing modules and adding a fourth {@code -cli} module.
 *
 * <p>It lives in {@code rvsec-crysl-crysl}, which therefore declares a dependency on
 * {@code rvsec-crysl-mop}. Two reasons, in order of weight:
 *
 * <ol>
 *   <li><strong>This is the module the single-JVM probe actually ran in.</strong> D-01 rests on a
 *       measurement — both parsers on one classpath under {@code guava.version = 33.5.0-jre} — and
 *       the classpath that was measured is this one. {@code CrySLParser} is what forces the Guava
 *       override (INV-CONF-16); {@code javamop} pulls no Guava at all, so adding it here moves
 *       nothing that the probe did not already cover. The reverse direction — putting the CLI in
 *       {@code -mop} and adding {@code -crysl} to it — would drag {@code CrySLParser}, Guice 7 and
 *       the whole Xtext tree onto the module whose {@code DependencyDisciplineTest} asserts that
 *       Guava is <em>absent</em> from it, and would invalidate that assertion's meaning.
 *   <li><strong>A fourth module would contradict D-01 as recorded.</strong> The decision is "one JVM
 *       and three Maven modules"; a {@code -cli} module is a fourth, and inventing it to host a
 *       {@code main} would be a structural change made for a convenience, not for a measured
 *       reason.
 * </ol>
 *
 * <p>The cost is stated rather than hidden: {@code -crysl} is no longer the smaller half of the two
 * lift modules, and a future reader may find its dependency on {@code -mop} surprising. The
 * dependency is one-directional — nothing in {@code -mop} refers to {@code -crysl} — and the arch
 * rules of both modules still hold, including {@code ModelShapeArchTest}'s "the model module
 * depends on neither parser", which constrains {@code -core} and is untouched by this.
 *
 * <h2>What is here and what is not</h2>
 *
 * <p>The shape follows {@code rvsec-mop-extractor} — {@code main} plus JCommander argument objects
 * plus a facade call — and not its code (D-15). Three subcommands: {@code compare} (M0–M4 against
 * the single upstream oracle), {@code lower} ({@code mop.lower} plus the round-trip gate) and
 * {@code calibrate} (the calibration gate on its own).
 *
 * <p>All three are wired.
 * {@link br.unb.cic.rvsec.crysl.crysl.cli.CompareRun} runs M0–M4 through
 * {@code core.compare.Pipeline} and emits JSON, CSV and Markdown;
 * {@link br.unb.cic.rvsec.crysl.crysl.cli.LowerRun} lowers each specification and runs the
 * round-trip gate over what came out.
 *
 * <p>{@link br.unb.cic.rvsec.crysl.crysl.cli.CalibrateRun} measures the eight calibration
 * quantities from the corpora themselves rather than from an emitted report — five of the eight are
 * about corpora {@code compare} never reads — and checks each against the independent route that
 * produced its target. It prints the whole report and then exits
 * {@link br.unb.cic.rvsec.crysl.crysl.cli.ExitCode#CALIBRATION_MISMATCH} if a target was not
 * reproduced. A gate that always passed would be worse than no gate: an instrument whose whole
 * purpose is to stop reporting greens that have nothing behind them cannot ship a subcommand that
 * exits {@code 0} without checking anything.
 *
 * <p>No subcommand measures an empty corpus: a directory holding no {@code *.mop} file
 * is a {@code CorpusReadError}, because a report of zero rows that exits {@code 0} is that same
 * green under another name.
 */
package br.unb.cic.rvsec.crysl.crysl.cli;
