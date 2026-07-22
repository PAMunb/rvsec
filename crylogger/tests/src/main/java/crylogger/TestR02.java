package crylogger;

import java.security.Key;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;

/**
 * Don't use insecure algorithms (e.g., RC2, RC4, IDEA, ..)
 *
 */
public class TestR02 {

	public void execute(boolean fail) throws Exception {
		if (fail) {
			executeFail();
		} else {
			executeSuccess();
		}
	}

	private void executeSuccess() throws Exception {
		Util.simpleGCM("text_to_encrypt");
	}

	private void executeFail() throws Exception {
		String alg = "DES";
		Key key = KeyGenerator.getInstance(alg).generateKey();

		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key);
		cipher.doFinal("text_to_encrypt".getBytes());
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR02().execute(fail);
	}

}
