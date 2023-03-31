package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;

/**
 * Don't use a static (constant) key for encryption
 *
 */
public class TestR05 {
	private static final String ENCRYPTION_KEY = "RwcmlVpg";

	public void execute(boolean fail) throws Exception {
		AlgorithmParameterSpec iv = Util.makeIv();

		Key key = null;
		if (fail) {
			key = Util.makeKey(ENCRYPTION_KEY);
		} else {
			key = Util.makeKey();
		}

		Util.encrypt("text_to_encrypt", key, iv);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR05().execute(fail);
	}

}
