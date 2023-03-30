package crylogger;

/**
 * Don't use a static (constant) password for PBE
 *
 */
public class TestR16 {

	public void execute(boolean fail) throws Exception {
		byte[] salt = Util.makeSalt();
		int iterationCount = Util.makeIterationCount();

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
		new TestR16().execute(fail);
	}

}
