package br.unb.cic.rv.pointcut;

import java.util.ArrayList;
import java.util.List;

/**
 * Recursive-descent parser for AspectJ pointcut expressions emitted by JavaMOP.
 *
 * <p>Grammar (see {@link PointcutExpression} for the high-level shape):
 * <pre>
 *   or      := and ('||' and)*
 *   and     := unary ('&amp;&amp;' unary)*
 *   unary   := '!' unary | primary
 *   primary := '(' or ')'
 *            | keyword '(' body ')'      // call/execution/args/target/within/staticinitialization/if/adviceexecution
 *            | namedRef                   // e.g. BaseAspect.notwithin()
 * </pre>
 *
 * <p>{@code body} is read as the balanced-parentheses suffix up to the matching
 * {@code ')'}. For {@code call(...)} and {@code staticinitialization(...)} the body
 * has its own structure — parsed by {@link #parseCallBody} / {@link #parseStaticInitBody}.
 *
 * <p>Unknown keywords become {@link NamedRefPC} so parsing never aborts on an
 * unrecognized reference; the weaver decides how to interpret these (typically
 * treat-as-true).
 */
public final class PointcutExpressionParser {

    private final String src;
    private int pos;

    private PointcutExpressionParser(String src) {
        this.src = src;
        this.pos = 0;
    }

    public static PointcutExpression parse(String expression) {
        if (expression == null || expression.isBlank()) {
            throw new PointcutParseException("empty pointcut expression");
        }
        PointcutExpressionParser p = new PointcutExpressionParser(expression.trim());
        PointcutExpression result = p.parseOr();
        p.skipWs();
        if (p.pos < p.src.length()) {
            throw new PointcutParseException(
                    "trailing characters at offset " + p.pos + " in: " + expression);
        }
        return result;
    }

    // --- expression grammar --------------------------------------------------

    private PointcutExpression parseOr() {
        PointcutExpression left = parseAnd();
        while (peekOp("||")) {
            consume("||");
            PointcutExpression right = parseAnd();
            left = new CombinedPC(CombinedPC.Op.OR, left, right);
        }
        return left;
    }

    private PointcutExpression parseAnd() {
        PointcutExpression left = parseUnary();
        while (peekOp("&&")) {
            consume("&&");
            PointcutExpression right = parseUnary();
            left = new CombinedPC(CombinedPC.Op.AND, left, right);
        }
        return left;
    }

    private PointcutExpression parseUnary() {
        skipWs();
        if (peekChar('!')) {
            pos++;
            skipWs();
            // !within(...) is the dominant negation in our corpus; we
            // specialize to NotWithinPC so matchers don't have to re-check
            // the inner shape.
            if (peekKeyword("within")) {
                consumeKeyword("within");
                String body = readParenBody();
                return new NotWithinPC(body.trim());
            }
            // Generic negation over other primary nodes: wrap in a NamedRef
            // that preserves the inner text; matchers rarely encounter this
            // in rv-monitor-generated expressions.
            PointcutExpression inner = parsePrimary();
            return new NamedRefPC("!" + asText(inner));
        }
        return parsePrimary();
    }

    private PointcutExpression parsePrimary() {
        skipWs();
        if (pos >= src.length()) {
            throw new PointcutParseException("unexpected end of expression");
        }
        if (peekChar('(')) {
            pos++;
            PointcutExpression inner = parseOr();
            skipWs();
            expectChar(')');
            return inner;
        }
        String keyword = readKeyword();
        if (keyword.isEmpty()) {
            throw new PointcutParseException(
                    "expected pointcut keyword at offset " + pos + " in: " + src);
        }
        skipWs();
        if (!peekChar('(')) {
            // A bare identifier with no parens — treat as named reference token.
            return new NamedRefPC(keyword);
        }
        String body = readParenBody();
        return dispatch(keyword, body);
    }

    private PointcutExpression dispatch(String keyword, String body) {
        switch (keyword) {
            case "call":                  return parseCallBody(body);
            case "execution":             return new ExecutionPC(body.trim());
            case "args":                  return parseArgsBody(body);
            case "target":                return new TargetPC(body.trim());
            case "within":                return new WithinPC(body.trim());
            case "staticinitialization":  return new StaticInitPC(body.trim());
            case "if":                    return new IfPC(body.trim());
            case "adviceexecution":       return new NamedRefPC("adviceexecution()");
            default:                      return new NamedRefPC(keyword + "(" + body + ")");
        }
    }

    // --- call(...) body parser -----------------------------------------------

    private static CallPC parseCallBody(String body) {
        // Strip optional modifier prefix (public/private/...).
        String s = body.trim();
        s = stripModifiers(s);

        // Constructor: <owner>.new(<params>)
        int newIdx = indexOfOwnerDotNew(s);
        if (newIdx >= 0) {
            String owner = s.substring(0, newIdx).trim();
            int openParen = s.indexOf('(', newIdx);
            int closeParen = matchingClose(s, openParen);
            String params = s.substring(openParen + 1, closeParen);
            CallPC.ParamList paramList = splitParams(params);
            return new CallPC(true, "", owner, "<init>",
                    paramList.head(), paramList.trailingVarargs());
        }

        // Method: <return> <owner>.<name>(<params>)
        int firstSpace = s.indexOf(' ');
        if (firstSpace < 0) {
            throw new PointcutParseException("malformed call() body: " + body);
        }
        String returnType = s.substring(0, firstSpace).trim();
        String rest = s.substring(firstSpace + 1).trim();
        int openParen = rest.indexOf('(');
        if (openParen < 0) {
            throw new PointcutParseException("malformed call() body (no '(' ): " + body);
        }
        String ownerAndName = rest.substring(0, openParen).trim();
        int lastDot = ownerAndName.lastIndexOf('.');
        if (lastDot < 0) {
            throw new PointcutParseException(
                    "malformed call() body (no owner.method): " + body);
        }
        String owner = ownerAndName.substring(0, lastDot);
        String name = ownerAndName.substring(lastDot + 1);
        int closeParen = matchingClose(rest, openParen);
        String params = rest.substring(openParen + 1, closeParen);
        CallPC.ParamList paramList = splitParams(params);
        return new CallPC(false, returnType, owner, name,
                paramList.head(), paramList.trailingVarargs());
    }

    private static ArgsPC parseArgsBody(String body) {
        List<String> names = new ArrayList<>();
        for (String part : body.split(",")) {
            String n = part.trim();
            if (n.isEmpty() || "..".equals(n)) continue;
            names.add(n);
        }
        return new ArgsPC(names);
    }

    // --- tokenization helpers ------------------------------------------------

    private static final String[] MODIFIERS = {
            "public", "private", "protected", "static", "final",
            "abstract", "synchronized", "native"
    };

    private static String stripModifiers(String body) {
        String s = body;
        boolean stripped;
        do {
            stripped = false;
            for (String mod : MODIFIERS) {
                if (s.startsWith(mod) && s.length() > mod.length()
                        && Character.isWhitespace(s.charAt(mod.length()))) {
                    s = s.substring(mod.length()).trim();
                    stripped = true;
                    break;
                }
            }
        } while (stripped);
        return s;
    }

    /** Locate {@code <owner>.new} preceding an opening paren, returning the index of {@code .new}. */
    private static int indexOfOwnerDotNew(String s) {
        int idx = 0;
        while (true) {
            int dotNew = s.indexOf(".new", idx);
            if (dotNew < 0) return -1;
            // Ensure .new is followed by ( (ignoring whitespace).
            int after = dotNew + ".new".length();
            while (after < s.length() && Character.isWhitespace(s.charAt(after))) after++;
            if (after < s.length() && s.charAt(after) == '(') {
                return dotNew;
            }
            idx = dotNew + 1;
        }
    }

    private static int matchingClose(String s, int openIdx) {
        int depth = 0;
        for (int i = openIdx; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '(') depth++;
            else if (c == ')') {
                depth--;
                if (depth == 0) return i;
            }
        }
        throw new PointcutParseException("unbalanced parens in: " + s);
    }

    /**
     * Split a {@code call()} param list into a fixed positional head plus a
     * trailing-varargs flag. A trailing {@code ..} (the AspectJ varargs
     * sentinel) sets {@code trailingVarargs} and is dropped from the head;
     * this covers both standalone {@code (..)} (empty head, match-anything)
     * and trailing-mixed {@code (String, ..)} (head {@code [String]}, tail
     * accepts any). Trailing {@code +} on a head param marks the AspectJ
     * subtype operator and is captured in {@link CallPC.ParamSpec#isSubtype()}
     * — the descriptor itself does not carry the {@code +}. Array forms
     * ({@code Foo[]}) keep their literal descriptors and are never marked
     * subtype.
     */
    private static CallPC.ParamList splitParams(String params) {
        List<CallPC.ParamSpec> head = new ArrayList<>();
        String s = params.trim();
        if (s.isEmpty()) return new CallPC.ParamList(head, false);
        String[] parts = s.split(",");
        boolean trailingVarargs = "..".equals(parts[parts.length - 1].trim());
        // A trailing ".." only marks varargs; it is never a head element.
        int headCount = trailingVarargs ? parts.length - 1 : parts.length;
        for (int i = 0; i < headCount; i++) {
            String p = parts[i].trim();
            boolean isSubtype = false;
            // Array forms (Foo[]) keep their literal descriptor; only a true
            // trailing "+" denotes subtype.
            if (p.endsWith("+")) {
                isSubtype = true;
                p = p.substring(0, p.length() - 1).trim();
            }
            head.add(new CallPC.ParamSpec(p, isSubtype));
        }
        return new CallPC.ParamList(head, trailingVarargs);
    }

    // --- cursor primitives ---------------------------------------------------

    private void skipWs() {
        while (pos < src.length() && Character.isWhitespace(src.charAt(pos))) {
            pos++;
        }
    }

    private boolean peekChar(char c) {
        skipWs();
        return pos < src.length() && src.charAt(pos) == c;
    }

    private boolean peekOp(String op) {
        skipWs();
        return src.regionMatches(pos, op, 0, op.length());
    }

    private boolean peekKeyword(String kw) {
        skipWs();
        if (!src.regionMatches(pos, kw, 0, kw.length())) return false;
        int end = pos + kw.length();
        return end == src.length() || !isIdentPart(src.charAt(end));
    }

    private void consume(String op) {
        skipWs();
        if (!src.regionMatches(pos, op, 0, op.length())) {
            throw new PointcutParseException("expected '" + op + "' at offset " + pos);
        }
        pos += op.length();
    }

    private void consumeKeyword(String kw) {
        skipWs();
        if (!peekKeyword(kw)) {
            throw new PointcutParseException("expected keyword '" + kw + "' at offset " + pos);
        }
        pos += kw.length();
    }

    private void expectChar(char c) {
        skipWs();
        if (pos >= src.length() || src.charAt(pos) != c) {
            throw new PointcutParseException("expected '" + c + "' at offset " + pos);
        }
        pos++;
    }

    /** Read a keyword or qualified identifier (may contain dots, e.g. {@code BaseAspect.notwithin}). */
    private String readKeyword() {
        skipWs();
        int start = pos;
        while (pos < src.length() && isIdentPart(src.charAt(pos))) {
            pos++;
        }
        return src.substring(start, pos);
    }

    /** Read the balanced parenthesized body starting at the current {@code (}. */
    private String readParenBody() {
        skipWs();
        expectChar('(');
        int start = pos;
        int depth = 1;
        while (pos < src.length()) {
            char c = src.charAt(pos);
            if (c == '(') depth++;
            else if (c == ')') {
                depth--;
                if (depth == 0) {
                    String body = src.substring(start, pos);
                    pos++;
                    return body;
                }
            }
            pos++;
        }
        throw new PointcutParseException("unterminated parenthesized body at offset " + start);
    }

    private static boolean isIdentPart(char c) {
        return Character.isLetterOrDigit(c) || c == '_' || c == '$' || c == '.';
    }

    private static String asText(PointcutExpression e) {
        return e.toString();
    }
}
