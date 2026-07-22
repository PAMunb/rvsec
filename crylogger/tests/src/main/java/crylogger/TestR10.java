package crylogger;

/**
 * Don't use a static (constant) salt for key derivation
 *
 */
public class TestR10 {

	public void execute(boolean fail) throws Exception {
		char[] password = Util.makePassword();
		int iterationCount = Util.makeIterationCount();

		byte[] salt = null;
		if (fail) {
			salt = "123".getBytes();
		} else {
			salt = Util.makeSalt();
		}

		Util.generatePBEKey(password, salt, iterationCount);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR10().execute(fail);
	}

}
