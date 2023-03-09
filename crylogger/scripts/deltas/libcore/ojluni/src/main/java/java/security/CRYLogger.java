/* CRYLOGGER: Author: Luca Piccolboni (piccolboni@cs.columbia.edu) */

package java.security;

import java.io.FileOutputStream;
import java.io.IOException;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Class to log cryptographic uses and misues =).
 */
public class CRYLogger {

	private static final String CRYLOGGER_ENV_PACKAGE_PREFIX = "CRYLOGGER_PACKAGE_PREFIX";
	private static FileOutputStream stream;

	/**
	 * Write the specified string in the log file.
	 *
	 * @param string the string to be written.
	 */
	synchronized static public void write(String string) {
		try {
			openOutputFile();

			stream.write(insertStackTrace(string).getBytes());
//			stream.write(string.getBytes());
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	static String insertStackTrace(String string) {
		StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();

		String packagePrefix = System.getenv(CRYLOGGER_ENV_PACKAGE_PREFIX);
		String text = string.replaceAll("\n", "");

		String trace = Stream.of(stackTrace)
//				.limit(20)
				.filter(t -> hasEnvPackagePrefix(packagePrefix)?t.getClassName().startsWith(packagePrefix):true)
				.map(t -> String.format("%s.%s", t.getClassName(), t.getMethodName()))//, t.getLineNumber()))
				.collect(Collectors.joining(",", "[", "]"));

		return text + " :: " + trace + "\n";
	}
	
	static boolean hasEnvPackagePrefix(String packagePrefix) {
		return packagePrefix != null && !"".equals(packagePrefix.trim());
	}

	synchronized static void openOutputFile() throws IOException {
		if (stream == null) {
			String filePath = System.getProperty("java.io.tmpdir");
			String fileName = filePath + "/application.cryptolog";
			String startMsg = "[CRYLogger] start logging here\n";
			stream = new FileOutputStream(fileName, true);
			stream.write(startMsg.getBytes());
		}
	}

	/**
	 * Write the specified string and the byte array in the log file.
	 *
	 * @param string the string to be written.
	 * @param array  the byte array to be written.
	 */
	synchronized static public void write(String string, byte[] array) {
		try {
			openOutputFile();

			StringBuilder sb = new StringBuilder();

			sb.append(string.getBytes());
//			stream.write(string.getBytes());

			if (array != null) {
				for (byte b : array) {
					sb.append((String.format("%02x", b)).getBytes());
//					stream.write((String.format("%02x", b)).getBytes());
				}
				sb.append("\n".getBytes());
//				stream.write("\n".getBytes());
			} else {
				sb.append("null\n".getBytes());
//				stream.write("null\n".getBytes());
			}

			stream.write(insertStackTrace(sb.toString()).getBytes());
		} catch (Exception e) {
			e.printStackTrace();
		}
	}
}
