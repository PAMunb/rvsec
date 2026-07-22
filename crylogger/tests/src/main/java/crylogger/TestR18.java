package crylogger;

import java.security.SecureRandom;
import java.util.Random;

/**
 * Don't use insecure PRNG (java.util.Random)
 *
 */
public class TestR18 {

	public void execute(boolean fail) throws Exception {
		Random rand = null;
		if (fail) {
			rand = new Random();
		} else {
			rand = new SecureRandom();
		}
		rand.nextInt();
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR18().execute(fail);
	}

}
