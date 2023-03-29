package crylogger;

import java.security.Key;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.spec.AlgorithmParameterSpec;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class Util {
	
	public static AlgorithmParameterSpec makeIv() {
		return makeIv(null, false);
	}
	public static AlgorithmParameterSpec makeIv(String str) {
		return makeIv(str, true);
	}
	public static AlgorithmParameterSpec makeIv(String str, boolean fail) {
		try {
			if(fail) {
				return new IvParameterSpec(str.getBytes("UTF-8"));
			}
			SecureRandom random = new SecureRandom();
			byte[] seed = new byte[16];
			random.nextBytes(seed);
			return new IvParameterSpec(seed);			
		} catch (Exception e) {
			e.printStackTrace();
		}
		return null;
	}

	public static Key makeKey() {
		return  makeKey(null, false);
	}
	public static Key makeKey(String str) {
		return  makeKey(str, true);
	}
	public static Key makeKey(String str, boolean fail) {
		try {
			byte[] key = null;
			
			if(fail) {
				MessageDigest md = MessageDigest.getInstance("SHA-256");
				key = md.digest(str.getBytes("UTF-8"));
			} else {
				SecureRandom random = new SecureRandom();
				byte[] seed = new byte[32];			
				random.nextBytes(seed);
				key = seed;
			}

			return new SecretKeySpec(key, "AES");
		} catch (Exception e) {
			e.printStackTrace();
		}

		return null;
	}
	
	public static byte[] simpleGCM(String text) throws Exception {
		String alg = "AES/GCM/NoPadding";
		Key key = makeKey();

		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key);
		return cipher.doFinal("text_to_encrypt".getBytes());
	}
	
	public static boolean parseArgs(String[] args) {
		boolean fail = false;
		if(args != null && args.length == 1) {
			if("true".equals(args[0].toLowerCase())) {
				fail = true;
			}
		}
		return fail;
	}
}
