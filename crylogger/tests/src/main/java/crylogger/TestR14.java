package crylogger;

/**
 * Don't use a weak password (score < 3) for PBE
 *
 */
public class TestR14 {

	public void execute(boolean fail) throws Exception {
		int iterationCount = Util.makeIterationCount();
		byte[] salt = Util.makeSalt();

		char[] password = null;
		if (fail) {
			password = "123".toCharArray();
		} else {
			password = Util.makePassword();
		}

		Util.generatePBEKey(password, salt, iterationCount);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR14().execute(fail);
	}

}
