package crylogger;

/**
 * Don't use NIST-black-listed passwords for PBE
 *
 */
public class TestR15 {

	public void execute(boolean fail) throws Exception {
		int iterationCount = Util.makeIterationCount();
		byte[] salt = Util.makeSalt();

		char[] password = null;
		if (fail) {
			password = "password".toCharArray();
		} else {
			password = Util.makePassword();
		}

		Util.generatePBEKey(password, salt, iterationCount);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR15().execute(fail);
	}

}
