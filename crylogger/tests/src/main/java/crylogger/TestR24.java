package crylogger;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URL;
import java.net.URLConnection;
import java.security.cert.X509Certificate;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

/**
 * Don't verify the hostname for SSL connections
 *
 */
public class TestR24 {
	private static SSLSocketFactory defaultFactory = null;
	private static HostnameVerifier defaultHostnameVerifier;

	public void execute(boolean fail) throws Exception {
		String requestUrl = "http://www.google.com";
		System.out.println("Testing on: " + requestUrl);

		defaultFactory = HttpsURLConnection.getDefaultSSLSocketFactory();
		defaultHostnameVerifier = HttpsURLConnection.getDefaultHostnameVerifier();

		if (fail) {
			executeFail(requestUrl);
		} else {
			executeSuccess(requestUrl);
		}

		URL url = new URL(requestUrl);
		URLConnection con = url.openConnection();

		consumeInput(con);
	}

	private void executeSuccess(String requestUrl) throws Exception {
		// Restore default factories
		HttpsURLConnection.setDefaultSSLSocketFactory(defaultFactory);
		HttpsURLConnection.setDefaultHostnameVerifier(defaultHostnameVerifier);
	}

	private void executeFail(String requestUrl) throws Exception {
		// Create a dummy all-trusting trust manager
		TrustManager[] dummyTrustManager = { new DummyTrustManager() };

		// Install the all-trusting trust manager
		SSLContext sslContext = SSLContext.getInstance("SSL");
		sslContext.init(null, dummyTrustManager, new java.security.SecureRandom());
		HttpsURLConnection.setDefaultSSLSocketFactory(sslContext.getSocketFactory());

		// Create and install all-trusting host name verifier
		HostnameVerifier dummyHostnameVerifier = new DummyHostnameVerifier();
		HttpsURLConnection.setDefaultHostnameVerifier(dummyHostnameVerifier);
	}

	private static void consumeInput(URLConnection con) throws Exception {
		InputStream istr = con.getInputStream();
		BufferedReader inp1 = new BufferedReader(new InputStreamReader(istr));
		String line;
		System.out.println(" -- Start Response (10 lines) --");
		int nl = 0;
		while ((nl < 10) && (line = inp1.readLine()) != null) {
			System.out.println(line);
			nl++;
		}
		System.out.println(" -- End Response --");
		inp1.close();
	}

	private static class DummyTrustManager implements X509TrustManager {
		@Override
		public java.security.cert.X509Certificate[] getAcceptedIssuers() {
			return null;
		}

		@Override
		public void checkClientTrusted(X509Certificate[] certs, String authType) {
		}

		@Override
		public void checkServerTrusted(X509Certificate[] certs, String authType) {
		}
	}

	private static class DummyHostnameVerifier implements HostnameVerifier {
		@Override
		public boolean verify(String hostname, SSLSession session) {
			return true;
		}
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR24().execute(fail);
	}

}
