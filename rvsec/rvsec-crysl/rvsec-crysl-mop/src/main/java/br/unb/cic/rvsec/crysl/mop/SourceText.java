package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The {@code .mop} file as text, with comments blanked out and character offsets preserved, plus
 * the line index that turns an offset into a {@link Provenance}.
 *
 * <p>This class exists because provenance cannot come from the AST. The parser fabricates
 * positions: {@code JavaParserAdapter} builds {@code MOPSpecFileExt}, {@code JavaMOPSpecExt} and
 * {@code PropertyAndHandlersExt} with the literal coordinates {@code (0, 0)}, and every event,
 * handler and declaration block is re-parsed out of a detached string ("Java bubble"), so its
 * {@code getBeginLine()} is a line number inside that bubble — 1 — and not inside the file. So the
 * component runs a parallel scan over the text, and that scan is the only source of {@code
 * file:line} on the MOP side (design D-19).
 *
 * <p>Comments are blanked rather than removed so that offsets keep mapping to the original file: a
 * removal would shift every position after it. Blanking is also what makes the scan honest — the
 * corpus contains commented-out idiom calls that must not be counted, for instance
 * {@code jca_android/MacSpec.mop:254}, a prose comment that names {@code validateAbsent} thirteen
 * lines above the one real {@code validateAbsent} call in the file.
 */
public final class SourceText {

    private final String file;
    private final String raw;
    private final String code;
    /** {@code lineStart[i]} is the offset of the first character of line {@code i + 1}. */
    private final int[] lineStart;

    private SourceText(String file, String raw, String code, int[] lineStart) {
        this.file = file;
        this.raw = raw;
        this.code = code;
        this.lineStart = lineStart;
    }

    /** Reads a file as UTF-8 and blanks its comments. */
    public static SourceText read(Path path) {
        String raw;
        try {
            raw = new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read " + path, e);
        }
        return of(path.getFileName().toString(), raw);
    }

    /** Builds the view over text already in memory; the name is what {@link Provenance} carries. */
    public static SourceText of(String file, String raw) {
        return new SourceText(file, raw, blankComments(raw), lineStarts(raw));
    }

    /**
     * The text with every comment character replaced by a space, newlines and length preserved.
     *
     * <p>String and character literals are tracked, because a {@code //} inside a literal is not a
     * comment; the corpus writes message literals with slashes in them ({@code "HMAC/SHA256"}), and
     * a naive scan that took the first {@code //} would blank the rest of a live line.
     */
    private static String blankComments(String raw) {
        char[] out = raw.toCharArray();
        int i = 0;
        int n = out.length;
        while (i < n) {
            char c = out[i];
            if (c == '"' || c == '\'') {
                char quote = c;
                i++;
                while (i < n && out[i] != quote) {
                    if (out[i] == '\\') {
                        i++;
                    }
                    i++;
                }
                i++;
            } else if (c == '/' && i + 1 < n && out[i + 1] == '/') {
                while (i < n && out[i] != '\n') {
                    out[i++] = ' ';
                }
            } else if (c == '/' && i + 1 < n && out[i + 1] == '*') {
                while (i < n && !(out[i] == '*' && i + 1 < n && out[i + 1] == '/')) {
                    if (out[i] != '\n') {
                        out[i] = ' ';
                    }
                    i++;
                }
                if (i < n) {
                    out[i++] = ' ';
                }
                if (i < n) {
                    out[i++] = ' ';
                }
            } else {
                i++;
            }
        }
        return new String(out);
    }

    private static int[] lineStarts(String raw) {
        List<Integer> starts = new ArrayList<>();
        starts.add(0);
        for (int i = 0; i < raw.length(); i++) {
            if (raw.charAt(i) == '\n') {
                starts.add(i + 1);
            }
        }
        int[] array = new int[starts.size()];
        for (int i = 0; i < array.length; i++) {
            array[i] = starts.get(i);
        }
        return array;
    }

    /** The file name provenance is stamped with. */
    public String file() {
        return file;
    }

    /** The text with comments blanked; offsets are the offsets of the original file. */
    public String code() {
        return code;
    }

    /** The text exactly as written, comments included. */
    public String raw() {
        return raw;
    }

    /** The 1-based line the given character offset falls on. */
    public int lineAt(int offset) {
        int low = 0;
        int high = lineStart.length - 1;
        while (low < high) {
            int mid = (low + high + 1) >>> 1;
            if (lineStart[mid] <= offset) {
                low = mid;
            } else {
                high = mid - 1;
            }
        }
        return low + 1;
    }

    /** {@link Provenance} for the given character offset. */
    public Provenance at(int offset) {
        return new Provenance(file, lineAt(offset));
    }

    /**
     * The offset of the first match of {@code pattern} at or after {@code from}, or {@code -1}.
     * Searching in the comment-blanked text, so a match inside a comment cannot be found.
     */
    public int find(Pattern pattern, int from) {
        Matcher m = pattern.matcher(code);
        return m.find(Math.max(0, from)) ? m.start() : -1;
    }

    /**
     * The offset just past the closing parenthesis of the argument list that starts at
     * {@code openParen}, or {@code -1} if the parentheses do not balance before end of file.
     * Parenthesis counting is aware of literals for the same reason {@link #blankComments} is.
     */
    public int matchParen(int openParen) {
        int depth = 0;
        for (int i = openParen; i < code.length(); i++) {
            char c = code.charAt(i);
            if (c == '"' || c == '\'') {
                char quote = c;
                i++;
                while (i < code.length() && code.charAt(i) != quote) {
                    if (code.charAt(i) == '\\') {
                        i++;
                    }
                    i++;
                }
            } else if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) {
                    return i + 1;
                }
            }
        }
        return -1;
    }

    /**
     * Splits an argument list at top-level commas. Nested calls, indexes and literals keep their
     * commas: {@code ensure(Property.GENERATED_KEY, k, k.getAlgorithm())} has two arguments after
     * the property, not three.
     *
     * <p>Only {@code (} and {@code [} open a nesting level. Angle brackets deliberately do not:
     * {@code <} and {@code >} are comparison operators far more often than type arguments in an
     * argument expression, and counting them would make a comparison swallow the comma after it.
     */
    public static List<String> splitArguments(String argumentList) {
        List<String> out = new ArrayList<>();
        int depth = 0;
        StringBuilder current = new StringBuilder();
        for (int i = 0; i < argumentList.length(); i++) {
            char c = argumentList.charAt(i);
            if (c == '"' || c == '\'') {
                char quote = c;
                current.append(c);
                i++;
                while (i < argumentList.length() && argumentList.charAt(i) != quote) {
                    if (argumentList.charAt(i) == '\\') {
                        current.append(argumentList.charAt(i++));
                    }
                    current.append(argumentList.charAt(i++));
                }
                if (i < argumentList.length()) {
                    current.append(argumentList.charAt(i));
                }
            } else if (c == '(' || c == '[') {
                depth++;
                current.append(c);
            } else if (c == ')' || c == ']') {
                depth--;
                current.append(c);
            } else if (c == ',' && depth <= 0) {
                out.add(current.toString().trim());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        String last = current.toString().trim();
        if (!last.isEmpty()) {
            out.add(last);
        }
        return out;
    }
}
