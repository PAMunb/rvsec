package presto.android.gui.clients;

import java.io.File;
import java.io.FileReader;
import java.io.InputStreamReader;
import java.io.BufferedReader;

import java.util.HashMap;
import java.util.Map;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

/**
 * Shared helper for integration tests that run GATOR on cryptoapp.apk.
 * Caches the analysis output so GATOR runs once even if multiple IT
 * classes use the result.
 *
 * Uses "bash -l -c ..." to ensure /etc/profile is sourced, which sets
 * up RVSEC_HOME, ANDROID_HOME, and other environment variables.
 */
class GatorTestHelper {

	/** The spec set the historical ITs run against; also the default `mopDir` in production. */
	static final String JCA = "jca";
	/** The verification fixture of the subtype/wildcard matching capability. */
	static final String GENERIC_NEW = "generic_new";

	// Keyed by spec set: a run against generic_new and a run against jca are different
	// analyses of the same APK, and several gates compare the two.
	private static final Map<String, File> cachedOutputFiles = new HashMap<>();
	private static final Map<String, JsonObject> cachedResults = new HashMap<>();
	private static final Map<String, String> cachedLogs = new HashMap<>();

	static synchronized File getOutputFile() throws Exception {
		return getOutputFile(JCA);
	}

	static synchronized File getOutputFile(String specSet) throws Exception {
		File cachedOutputFile = cachedOutputFiles.get(specSet);
		if (cachedOutputFile != null && cachedOutputFile.exists() && cachedOutputFile.length() > 0) {
			return cachedOutputFile;
		}

		String rvsecHome = System.getenv("RVSEC_HOME");
		if (rvsecHome == null || rvsecHome.isEmpty()) {
			throw new IllegalStateException("RVSEC_HOME not set");
		}

		String rvAndroid = rvsecHome + "/rv-android";
		String apkPath = rvAndroid + "/apks_examples/cryptoapp.apk";
		String clientJar = rvAndroid + "/lib/gator/rvsec-analysis-client.jar";
		String gatorDir = rvAndroid + "/lib/gator";
		String mopDir = rvsecHome + "/rvsec/rvsec-mop/src/main/resources/" + specSet;

		// Verify prerequisites
		if (!new File(apkPath).exists()) {
			throw new IllegalStateException("cryptoapp.apk not found: " + apkPath);
		}
		if (!new File(clientJar).exists()) {
			throw new IllegalStateException("rvsec-analysis-client.jar not found: " + clientJar);
		}
		if (!new File(gatorDir, "gator").exists()) {
			throw new IllegalStateException("gator launcher not found in: " + gatorDir);
		}

		// Output to temp file
		cachedOutputFile = File.createTempFile("cryptoapp-it-" + specSet + "-", ".json");
		cachedOutputFile.deleteOnExit();

		System.out.println("[GatorTestHelper] Running GATOR on cryptoapp.apk...");
		System.out.println("[GatorTestHelper] Output: " + cachedOutputFile.getAbsolutePath());

		// Use "bash -l" (login shell) to source /etc/profile which sets up
		// RVSEC_HOME, ANDROID_HOME, and other environment variables.
		// GATOR/Soot 3.3.0 runs on any Java 11+ (tested with Java 21).
		// rt.jar is NOT needed — android.jar provides all JCA classes (Spike Q6).
		//
		// The call-graph algorithm is left unset, so GATOR uses its compiled-in default —
		// spark, which is what production runs. This line passed `-withCHA` until 2026-08-28,
		// which made every IT here answer to a call graph the project does not ship, and that
		// is not a cosmetic difference: on cryptoapp, CHA reads 67 reachable / 61 reachesTarget
		// against spark's 55 / 33. Two things followed. The IT baseline
		// (test/resources/baseline/cryptoapp_baseline.json) and the parity gate's frozen fixture
		// (modules/rv-static-analysis/tests/resources/cryptoapp.apk.json) held different numbers
		// for the same APK — the gh60 §D12 stale-CHA incident, which repaired
		// scripts/check_signature_file_subset.py and never reached this file. And CHA
		// over-approximates enough to absorb the direct bytecode scan entirely
		// (`bytecode-only seeds: 0` for both spec sets), so the scan-only path that
		// BUG-INV-ANA-19 exists for could not be observed at all; under spark the same APK and
		// jar report 7 of them.
		String gatorCommand = String.format(
				"cd '%s' && ./gator a -p '%s' --client-jar '%s' --out '%s'"
						+ " -client RvsecAnalysisClient -clientParam 'mopDir=%s'"
						+ " --timeout 600",
				gatorDir, apkPath, clientJar,
				cachedOutputFile.getAbsolutePath(), mopDir);

		ProcessBuilder pb = new ProcessBuilder("bash", "-l", "-c", gatorCommand);
		pb.redirectErrorStream(true);

		Process process = pb.start();

		// Consume output to prevent blocking
		StringBuilder output = new StringBuilder();
		try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
			String line;
			while ((line = reader.readLine()) != null) {
				System.out.println("[GATOR] " + line);
				output.append(line).append("\n");
			}
		}

		int exitCode = process.waitFor();
		System.out.println("[GatorTestHelper] GATOR exit code: " + exitCode);

		if (exitCode != 0) {
			throw new RuntimeException("GATOR exited with code " + exitCode
					+ ". Output:\n" + output);
		}

		if (!cachedOutputFile.exists() || cachedOutputFile.length() == 0) {
			throw new RuntimeException("GATOR produced no output. "
					+ "File exists: " + cachedOutputFile.exists()
					+ ", size: " + (cachedOutputFile.exists() ? cachedOutputFile.length() : -1)
					+ ". GATOR output:\n" + output);
		}

		System.out.println("[GatorTestHelper] Analysis complete. Output size: "
				+ cachedOutputFile.length() + " bytes");

		cachedOutputFiles.put(specSet, cachedOutputFile);
		cachedLogs.put(specSet, output.toString());
		return cachedOutputFile;
	}

	static synchronized JsonObject getAnalysisResult() throws Exception {
		return getAnalysisResult(JCA);
	}

	static synchronized JsonObject getAnalysisResult(String specSet) throws Exception {
		JsonObject cached = cachedResults.get(specSet);
		if (cached != null) {
			return cached;
		}
		File outputFile = getOutputFile(specSet);
		try (FileReader reader = new FileReader(outputFile)) {
			JsonObject parsed = JsonParser.parseReader(reader).getAsJsonObject();
			cachedResults.put(specSet, parsed);
			return parsed;
		}
	}

	/**
	 * The GATOR stdout of the run for {@code specSet}. Several gates are about what the
	 * analysis <i>reported</i> — how many owners force-resolved, whether any degraded — and
	 * that lives in the log, not in the JSON.
	 */
	static synchronized String getAnalysisLog(String specSet) throws Exception {
		getOutputFile(specSet);
		return cachedLogs.getOrDefault(specSet, "");
	}
}
