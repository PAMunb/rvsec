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
		if (fail) {
			executeFail();
		} else {
			executeSuccess();
		}
	}

	private void executeSuccess() throws Exception {
		Key key = Util.makeKey();
		AlgorithmParameterSpec iv = Util.makeIv();

		Util.encrypt("text_to_encrypt", key, iv);
	}

	private void executeFail() throws Exception {
		Key key = Util.makeKey(ENCRYPTION_KEY);
		AlgorithmParameterSpec iv = Util.makeIv();

		Util.encrypt("text_to_encrypt", key, iv);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR05().execute(fail);
	}

}
