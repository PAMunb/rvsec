package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;

/**
 * Don't reuse the initialization vector and key pairs
 *
 */
public class TestR09 {
	private static final String ENCRYPTION_KEY = "RwcmlVpg";
	private static final String ENCRYPTION_IV = "4e5Wa71fYoT7MFEX";

	private static Key key;
	private static AlgorithmParameterSpec iv;

	public void execute(boolean fail) throws Exception {
		key = Util.makeKey(ENCRYPTION_KEY);
		iv = Util.makeIv(ENCRYPTION_IV);
		Util.encrypt("text_to_encrypt", key, iv);

		if (!fail) {
			key = Util.makeKey();
			iv = Util.makeIv();
		}

		Util.encrypt("text_to_encrypt", key, iv);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR09().execute(fail);
	}

}
