package br.unb.cic.rv.grammar.util;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import org.commonmark.ext.gfm.tables.TableBlock;
import org.commonmark.ext.gfm.tables.TableBody;
import org.commonmark.ext.gfm.tables.TableCell;
import org.commonmark.ext.gfm.tables.TableRow;
import org.commonmark.ext.gfm.tables.TablesExtension;
import org.commonmark.node.AbstractVisitor;
import org.commonmark.node.Code;
import org.commonmark.node.Heading;
import org.commonmark.node.Node;
import org.commonmark.node.Text;
import org.commonmark.parser.Parser;

/**
 * Parses the grammar coverage matrix table (the first table after the {@code ## Matrix} heading) of
 * {@code docs/aspectj_grammar_coverage.md} into {@link MatrixRow} records, on top of
 * {@code commonmark-java} (NOT a custom split parser — escaped pipes {@code \|} and code spans are
 * handled by the library). Cell values are the rendered text (code-span backticks stripped),
 * matching {@link AspectJDesignators#DESIGNATORS}.
 *
 * <p>Throws if the {@code ## Matrix} anchor is absent or duplicated, or if a row's column count is
 * not 9 (INV-INS-88 structural integrity).
 */
public final class MatrixMarkdownParser {

    /** One matrix row. Demand columns and verdict are kept as raw strings at this layer; typed
     *  accessors (verdict enum, per-corpus demand ints) are applied by {@code MatrixIntegrityTest}
     *  on the populated matrix, tolerating {@code "TBD"} during the §2-scaffold phase. */
    public record MatrixRow(String syntax, String sourceDemand, String pipelineDemand,
                            String parser, String matcher, String emitter,
                            String verdict, String evidence, String deferralNote) { }

    private static final int COLUMNS = 9;

    private MatrixMarkdownParser() { }

    /** Resolve the matrix at {@code $RVSEC_HOME/rv-android/docs/aspectj_grammar_coverage.md},
     *  overridable via the {@code gh62.matrix.path} system property. */
    public static Path defaultMatrixPath() {
        String override = System.getProperty("gh62.matrix.path");
        if (override != null && !override.isBlank()) {
            return Paths.get(override);
        }
        String home = System.getenv("RVSEC_HOME");
        if (home == null || home.isBlank()) {
            throw new IllegalStateException(
                    "RVSEC_HOME is not set and gh62.matrix.path is not provided — cannot resolve the matrix path");
        }
        return Paths.get(home, "rv-android", "docs", "aspectj_grammar_coverage.md");
    }

    /** Parse the matrix at {@link #defaultMatrixPath()}. */
    public static List<MatrixRow> parseDefault() {
        return parse(defaultMatrixPath());
    }

    /** Parse the matrix table from a markdown file. */
    public static List<MatrixRow> parse(Path markdownFile) {
        String content;
        try {
            content = Files.readString(markdownFile);
        } catch (IOException e) {
            throw new UncheckedIOException("failed to read matrix file " + markdownFile, e);
        }
        return parseString(content);
    }

    /** Parse the matrix table from a markdown string. */
    public static List<MatrixRow> parseString(String markdown) {
        Parser parser = Parser.builder()
                .extensions(List.of(TablesExtension.create()))
                .build();
        Node doc = parser.parse(markdown);

        TableBlock table = locateMatrixTable(doc);
        List<MatrixRow> rows = new ArrayList<>();
        TableBody body = findChild(table, TableBody.class);
        if (body == null) {
            throw new IllegalStateException("the `## Matrix` table has no body rows");
        }
        for (Node r = body.getFirstChild(); r != null; r = r.getNext()) {
            if (!(r instanceof TableRow row)) {
                continue;
            }
            List<String> cells = new ArrayList<>();
            for (Node c = row.getFirstChild(); c != null; c = c.getNext()) {
                if (c instanceof TableCell cell) {
                    cells.add(cellText(cell));
                }
            }
            if (cells.size() != COLUMNS) {
                throw new IllegalStateException("matrix row '" + (cells.isEmpty() ? "?" : cells.get(0))
                        + "' has " + cells.size() + " columns, expected " + COLUMNS);
            }
            rows.add(new MatrixRow(cells.get(0), cells.get(1), cells.get(2), cells.get(3),
                    cells.get(4), cells.get(5), cells.get(6), cells.get(7), cells.get(8)));
        }
        return rows;
    }

    /** Find the single TableBlock that immediately follows the unique level-2 "Matrix" heading. */
    private static TableBlock locateMatrixTable(Node doc) {
        int matrixHeadings = 0;
        TableBlock found = null;
        for (Node n = doc.getFirstChild(); n != null; n = n.getNext()) {
            if (n instanceof Heading h && h.getLevel() == 2 && "Matrix".equals(headingText(h))) {
                matrixHeadings++;
                // The first TableBlock after this heading is the matrix table.
                for (Node m = n.getNext(); m != null; m = m.getNext()) {
                    if (m instanceof TableBlock tb) {
                        found = tb;
                        break;
                    }
                    if (m instanceof Heading) {
                        break; // next section started before any table — anchor has no table
                    }
                }
            }
        }
        if (matrixHeadings == 0) {
            throw new IllegalStateException("`## Matrix` heading not found in the matrix document");
        }
        if (matrixHeadings > 1) {
            throw new IllegalStateException("`## Matrix` heading is duplicated (" + matrixHeadings + " occurrences)");
        }
        if (found == null) {
            throw new IllegalStateException("no table follows the `## Matrix` heading");
        }
        return found;
    }

    private static String headingText(Heading h) {
        StringBuilder sb = new StringBuilder();
        h.accept(new AbstractVisitor() {
            @Override
            public void visit(Text text) {
                sb.append(text.getLiteral());
            }
        });
        return sb.toString().trim();
    }

    /** Rendered text of a cell: concatenation of Text and Code literals (code-span backticks
     *  stripped; escaped pipes already unescaped by the parser). */
    private static String cellText(TableCell cell) {
        StringBuilder sb = new StringBuilder();
        cell.accept(new AbstractVisitor() {
            @Override
            public void visit(Text text) {
                sb.append(text.getLiteral());
            }

            @Override
            public void visit(Code code) {
                sb.append(code.getLiteral());
            }
        });
        return sb.toString().trim();
    }

    private static <T extends Node> T findChild(Node parent, Class<T> type) {
        for (Node n = parent.getFirstChild(); n != null; n = n.getNext()) {
            if (type.isInstance(n)) {
                return type.cast(n);
            }
        }
        return null;
    }
}
