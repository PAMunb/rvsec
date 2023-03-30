package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;
import java.util.Random;

import javax.crypto.spec.SecretKeySpec;

/**
 * Don't use a 'badly-derived' key for encryption
 *
 */
public class TestR06 {

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
		AlgorithmParameterSpec iv = Util.makeIv();

		Random random = new Random();
		byte[] seed = new byte[32];
		random.nextBytes(seed);
		Key key = new SecretKeySpec(seed, "AES");

		Util.encrypt("text_to_encrypt", key, iv);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR06().execute(fail);
	}

}
