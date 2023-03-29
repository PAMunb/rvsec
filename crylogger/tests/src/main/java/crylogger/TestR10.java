package crylogger;

import java.security.Key;
import java.security.SecureRandom;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

public class TestR10 {

	public void execute(boolean fail) throws Exception {		
		SecureRandom rand = new SecureRandom();
		byte[] salt = null;
		
		if(fail) {
			salt = "123".getBytes();
		} else {			
			salt = new byte[32];
			rand.nextBytes(salt);
		}
		
		String algo = "PBEWithSHA1andDESede";
		char[] password = "password".toCharArray();
		int iterationCount = rand.nextInt(2048);

		// encryption key
		PBEKeySpec encPBESpec = new PBEKeySpec(password, salt, iterationCount);
		SecretKeyFactory encKeyFact = SecretKeyFactory.getInstance(algo);
		Key encKey = encKeyFact.generateSecret(encPBESpec);		
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);		
		new TestR10().execute(fail);		
	}

}
