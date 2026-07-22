package presto.android.gui.clients;

import java.io.File;
import java.io.FileReader;
import java.io.InputStreamReader;
import java.io.BufferedReader;

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

	private static JsonObject cachedResult;
	private static File cachedOutputFile;

	static synchronized File getOutputFile() throws Exception {
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
		String mopDir = rvsecHome + "/rvsec/rvsec-mop/src/main/resources/jca";

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
		cachedOutputFile = File.createTempFile("cryptoapp-it-", ".json");
		cachedOutputFile.deleteOnExit();

		System.out.println("[GatorTestHelper] Running GATOR on cryptoapp.apk...");
		System.out.println("[GatorTestHelper] Output: " + cachedOutputFile.getAbsolutePath());

		// Use "bash -l" (login shell) to source /etc/profile which sets up
		// RVSEC_HOME, ANDROID_HOME, and other environment variables.
		// GATOR/Soot 3.3.0 runs on any Java 11+ (tested with Java 21).
		// rt.jar is NOT needed — android.jar provides all JCA classes (Spike Q6).
		String gatorCommand = String.format(
				"cd '%s' && ./gator a -p '%s' --client-jar '%s' --out '%s'"
						+ " -client RvsecAnalysisClient -clientParam 'mopDir=%s'"
						+ " -withCHA --timeout 600",
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

		return cachedOutputFile;
	}

	static synchronized JsonObject getAnalysisResult() throws Exception {
		if (cachedResult != null) {
			return cachedResult;
		}

		File outputFile = getOutputFile();
		try (FileReader reader = new FileReader(outputFile)) {
			cachedResult = JsonParser.parseReader(reader).getAsJsonObject();
		}
		return cachedResult;
	}
}
