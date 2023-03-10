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

	public static final String STACKTRACE_SEPARATOR = " :: ";
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
		} catch (Exception e) {
			e.printStackTrace();
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

			if (array != null) {
				for (byte b : array) {
					sb.append((String.format("%02x", b)).getBytes());
				}
				sb.append("\n".getBytes());
			} else {
				sb.append("null\n".getBytes());
			}

			stream.write(insertStackTrace(sb.toString()).getBytes());
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	static String insertStackTrace(String string) {
		StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();

		String text = string.replaceAll("\n", "");

		String trace = Stream.of(stackTrace)
//				.limit(20)
				.map(t -> String.format("%s.%s", t.getClassName(), t.getMethodName()))// , t.getLineNumber()))
				.collect(Collectors.joining(",", "[", "]"));

		return text + STACKTRACE_SEPARATOR + trace + "\n";
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

}
