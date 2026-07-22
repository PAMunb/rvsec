package crylogger;

import java.security.SecureRandom;

/**
 * Don't use a short salt (< 64 bits) for key derivation
 *
 */
public class TestR11 {

	public void execute(boolean fail) throws Exception {
		char[] password = Util.makePassword();
		int iterationCount = Util.makeIterationCount();

		int saltSize = 32;
		if (fail) {
			saltSize = 6;
		}
		byte[] salt = new byte[saltSize];
		new SecureRandom().nextBytes(salt);

		Util.generatePBEKey(password, salt, iterationCount);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR11().execute(fail);
	}

}
