package crylogger;

/**
 * Don't use < 1000 iterations for key derivation
 *
 */
public class TestR13 {

	public void execute(boolean fail) throws Exception {
		char[] password = Util.makePassword();
		byte[] salt = Util.makeSalt();

		int iterationCount = 999;
		if (!fail) {
			iterationCount = 10000;
		}

		Util.generatePBEKey(password, salt, iterationCount);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR13().execute(fail);
	}

}
