package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;

/**
 * Don't use a static (constant) initialization vector
 *
 */
public class TestR07 {
	private static final String ENCRYPTION_IV = "4e5Wa71fYoT7MFEX";

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
		Key key = Util.makeKey();
		AlgorithmParameterSpec iv = Util.makeIv(ENCRYPTION_IV);

		Util.encrypt("text_to_encrypt", key, iv);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR07().execute(fail);
	}

}
