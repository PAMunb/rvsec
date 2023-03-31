package crylogger;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLSocketFactory;

/**
 * Don't verify hostnames for SSL connections
 *
 */
public class TestR26 {

	public void execute(boolean fail) throws Exception {
		SSLSocketFactory.getDefault();

		if (!fail) {
			HttpsURLConnection.getDefaultHostnameVerifier();
		}
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR26().execute(fail);
	}

}
