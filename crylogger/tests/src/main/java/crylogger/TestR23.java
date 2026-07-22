package crylogger;

import java.security.KeyStore;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

/**
 * Don't use a static (constant) password for KeyStore
 *
 */
public class TestR23 {

	public void execute(boolean fail) throws Exception {
		String alias = "teste";
		char[] password = null;

		if (fail) {
			password = "123".toCharArray();
		} else {
			password = Util.makePassword();
		}

		KeyStore keyStore = KeyStore.getInstance("pkcs12");
		keyStore.load(null, password);

		KeyGenerator keygen = KeyGenerator.getInstance("HmacSHA256");
		SecretKey secretKey = keygen.generateKey();
		KeyStore.ProtectionParameter protParam = new KeyStore.PasswordProtection(password);
		KeyStore.SecretKeyEntry secretKeyEntry = new KeyStore.SecretKeyEntry(secretKey);

		keyStore.setEntry(alias, secretKeyEntry, protParam);

		KeyStore.Entry entry = keyStore.getEntry(alias, protParam);
	}

	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);
		new TestR23().execute(fail);
	}

}
