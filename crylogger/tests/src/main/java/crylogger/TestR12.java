package crylogger;

import java.security.SecureRandom;

/**
 * Don't use the salt for different purposes
 *
 */
public class TestR12 {

	public void execute(boolean fail) throws Exception {
		SecureRandom rand = new SecureRandom();
		char[] password = Util.makePassword();
		int iterationCount = Util.makeIterationCount();
		byte[] salt = "123".getBytes();

		if (!fail) {
			rand.nextBytes(salt);
		}
		Util.generatePBEKey(password, salt, iterationCount);

		if (!fail) {
			rand.nextBytes(salt);
		}
		Util.generatePBEKey(password, salt, iterationCount);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR12().execute(fail);
	}

}
