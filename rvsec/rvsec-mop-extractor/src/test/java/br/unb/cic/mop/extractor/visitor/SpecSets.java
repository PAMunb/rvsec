package br.unb.cic.mop.extractor.visitor;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Locates the real `.mop` corpora the extractor gates run against. They are read from
 * `rvsec-mop/src/main/resources/` rather than copied into `src/test/resources`, so a gate
 * can never pass against a stale snapshot of a corpus that is still being edited.
 */
final class SpecSets {

	private SpecSets() {
	}

	static String dir(String specSet) {
		// Surefire's working directory is the module basedir under a reactor build and under a
		// module-local one alike, so the sibling module resolves the same way in both.
		Path path = Paths.get("..", "rvsec-mop", "src", "main", "resources", specSet).toAbsolutePath().normalize();
		if (!path.toFile().isDirectory()) {
			throw new IllegalStateException("Spec set directory not found: " + path);
		}
		return path.toString();
	}

	/** Number of `.mop` files in a spec set — always enumerated, never hard-coded. */
	static int specCount(String specSet) {
		File[] files = new File(dir(specSet)).listFiles((d, name) -> name.endsWith(".mop"));
		return files == null ? 0 : files.length;
	}
}
