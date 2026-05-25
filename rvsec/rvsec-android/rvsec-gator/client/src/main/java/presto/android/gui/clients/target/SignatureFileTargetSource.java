package presto.android.gui.clients.target;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Loads target methods from a plain-text signature file (one Soot
 * signature per line). Lines starting with {@code #} (after optional
 * leading whitespace) and blank lines are ignored. Malformed lines
 * raise {@link IllegalArgumentException} carrying the offending file
 * path and 1-based line number (INV-ANA-34) so the operator can fix
 * the input rather than silently dropping entries.
 *
 * <p>Accepted forms (both Soot conventions):
 * <pre>
 *   &lt;javax.crypto.Cipher: void init(int,java.security.Key)&gt;
 *   &lt;javax.crypto.Cipher: void init(..)&gt;   // wildcard params → LENIENT entry
 *   &lt;javax.crypto.Cipher: void init(*)&gt;
 * </pre>
 *
 * <p>{@link TargetMethod.MatchPolicy#STRICT} is the default per entry;
 * any entry whose parameter list is the literal {@code ..} or {@code *}
 * is emitted as {@link TargetMethod.MatchPolicy#LENIENT} so the source
 * file can mix strict and lenient targets line-by-line. The downstream
 * bytecode scanner is LENIENT by construction (see D7 in design.md),
 * so a STRICT entry may still match parameter-mismatched call sites at
 * the bytecode-scan layer — STRICT only constrains the resolver's
 * Soot {@code Scene} matching.
 */
public final class SignatureFileTargetSource implements TargetMethodSource {

	// <className: returnType methodName(paramTypeList)>
	private static final Pattern SIGNATURE_PATTERN = Pattern.compile(
			"^<([^:]+):\\s+([^\\s]+)\\s+([^(]+)\\(([^)]*)\\)>$");

	private final Path signaturesFile;

	public SignatureFileTargetSource(Path signaturesFile) {
		this.signaturesFile = signaturesFile;
	}

	@Override
	public Set<TargetMethod> load() {
		List<String> lines;
		try {
			lines = Files.readAllLines(signaturesFile, StandardCharsets.UTF_8);
		} catch (IOException e) {
			throw new IllegalStateException(
					"Cannot read targets file: " + signaturesFile, e);
		}

		Set<TargetMethod> out = new HashSet<>();
		int lineNo = 0;
		for (String raw : lines) {
			lineNo++;
			String line = raw.trim();
			if (line.isEmpty() || line.startsWith("#")) {
				continue;
			}
			out.add(parseLine(line, lineNo));
		}
		return out;
	}

	private TargetMethod parseLine(String line, int lineNo) {
		Matcher m = SIGNATURE_PATTERN.matcher(line);
		if (!m.matches()) {
			throw new IllegalArgumentException(String.format(
					"Malformed Soot signature at %s:%d — expected "
							+ "'<className: returnType methodName(paramTypes)>', got: %s",
					signaturesFile, lineNo, line));
		}
		String className = m.group(1).trim();
		String methodName = m.group(3).trim();
		String paramList = m.group(4).trim();

		TargetMethod.MatchPolicy policy;
		List<String> params = new ArrayList<>();
		if ("..".equals(paramList) || "*".equals(paramList)) {
			policy = TargetMethod.MatchPolicy.LENIENT;
		} else {
			policy = TargetMethod.MatchPolicy.STRICT;
			if (!paramList.isEmpty()) {
				for (String p : paramList.split(",")) {
					params.add(p.trim());
				}
			}
		}
		return new TargetMethod(className, methodName, params, line, policy);
	}
}
