package crylogger;

import java.security.SecureRandom;
import java.util.Random;

/**
 * Don't use a static (constant) seed for PRNG
 *
 */
public class TestR17 {

	public void execute(boolean fail) throws Exception {

//		byte[] tmp = new byte[32];
		Random r = new SecureRandom();//"123".getBytes());
		r.setSeed(123);
//		r.nextBytes(tmp);
//
//		System.out.println(">>> "+Base64.getEncoder().encodeToString(tmp));
//
//		r.nextBytes(tmp);
//		System.out.println(">>> "+Base64.getEncoder().encodeToString(tmp));

		System.out.println("==" + r.nextInt());
		System.out.println("==" + r.nextInt());

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
