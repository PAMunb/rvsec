package crylogger;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;

/**
 * Don't use the padding PKCS1Padding for RSA
 *
 */
public class TestR21 {

	public void execute(boolean fail) throws Exception {
		if (fail) {
			testR21("RSA/ECB/PKCS1Padding");
		} else {
			testR21("RSA");
		}
	}

	static void testR21(String rsa) throws Exception {
		KeyPair pair = Util.generateKeyPair(2048);

		String secretMessage = "secret message";
		byte[] encryptedMessageBytes = Util.encrypt(secretMessage, pair.getPublic(), rsa);

		byte[] decryptedMessageBytes = Util.decrypt(encryptedMessageBytes, pair.getPrivate(), rsa);
		String decryptedMessage = new String(decryptedMessageBytes, StandardCharsets.UTF_8);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR21().execute(fail);
	}

}
