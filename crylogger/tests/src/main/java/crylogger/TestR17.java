package crylogger;

/**
 * Don't use a static (constant) seed for PRNG
 *
 */
public class TestR17 {

	public void execute(boolean fail) throws Exception {
		// JAVADOC SecureRandom.setSeed(): The given seed supplements,
	    // rather than replaces, the existing seed. Thus, repeated calls
	    // are guaranteed never to reduce randomness.

//		Random r = new SecureRandom();//"123".getBytes());
//		r.setSeed(123);
//		System.out.println("==" + r.nextInt());

		if (fail) {
			executeFail();
		} else {
			executeSuccess();
		}
	}

	private void executeSuccess() throws Exception {

	}

	private void executeFail() throws Exception {

	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR17().execute(fail);
	}

}
