package presto.android.gui.clients.json;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Reflection helper invoked by the Python-side parity test
 * ({@code tests/parity/json_keys.py}) via {@code subprocess.run(...)}.
 * Walks every {@code public static final String} field of
 * {@link JsonSchema.Keys} and prints the value on its own line, sorted
 * alphabetically so the diff between Java and Python is order-stable.
 *
 * <p>The parity test compares this output, line-by-line, against
 * {@code sorted(set(_JK.__dict__.values()))} in the Python parser. INV-ANA-32
 * says any divergence MUST surface as a test failure naming the missing
 * key on each side — the comparison is in the Python script; this dumper
 * only owns the Java half.
 */
public final class JsonSchemaKeysDump {

	private JsonSchemaKeysDump() {
		// utility
	}

	public static void main(String[] args) throws IllegalAccessException {
		List<String> values = new ArrayList<>();
		for (Field f : JsonSchema.Keys.class.getDeclaredFields()) {
			int mods = f.getModifiers();
			if (!Modifier.isStatic(mods) || !Modifier.isFinal(mods)
					|| f.getType() != String.class) {
				continue;
			}
			values.add((String) f.get(null));
		}
		Collections.sort(values);
		for (String v : values) {
			System.out.println(v);
		}
	}
}
