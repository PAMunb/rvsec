package crylogger;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;;

/**
 * Don't use insecure hash (e.g., MD2, MD4, SHA-1)
 *
 */
public class TestR01 {

	public void execute(boolean fail) throws NoSuchAlgorithmException {
		String alg = "SHA-256";
		if (fail) {
			alg = "MD5";
		}

		MessageDigest digest = MessageDigest.getInstance(alg);
		digest.digest("password".getBytes());
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR01().execute(fail);
	}

}
