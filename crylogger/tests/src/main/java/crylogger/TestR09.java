package crylogger;

import java.security.Key;
import java.security.spec.AlgorithmParameterSpec;

import javax.crypto.Cipher;

public class TestR09 {
	private static final String ENCRYPTION_KEY = "RwcmlVpg";
	private static final String ENCRYPTION_KEY2 = "RwcmlVph";
	private static final String ENCRYPTION_IV = "4e5Wa71fYoT7MFEX";
	private static final String ENCRYPTION_IV2 = "3e5Wa71fYoT7MFEX";
	
	private static Key key;
	private static AlgorithmParameterSpec iv;

	public void execute(boolean fail) throws Exception {
		key = Util.makeKey(ENCRYPTION_KEY);
		iv = Util.makeIv(ENCRYPTION_IV);
		encrypt("password");
		
		if(!fail) {
			key = Util.makeKey(ENCRYPTION_KEY2);
			iv = Util.makeIv(ENCRYPTION_IV2);
		} 	
		encrypt("password");
	}	
	
	private byte[] encrypt(String src) {
		try {
			Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
			cipher.init(Cipher.ENCRYPT_MODE, key, iv);
			return cipher.doFinal(src.getBytes());
		} catch (Exception e) {
			throw new RuntimeException(e);
		}
	}
	
	public static void main(String[] args) throws Exception {
		boolean fail = Util.parseArgs(args);		
		new TestR09().execute(fail);		
	}

}
