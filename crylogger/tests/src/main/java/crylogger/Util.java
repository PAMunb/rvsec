package crylogger;

import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.spec.AlgorithmParameterSpec;
import java.security.spec.InvalidKeySpecException;
import java.util.Random;

import javax.crypto.Cipher;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

public class Util {
	public static final String ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!@#$%&*";

	public static AlgorithmParameterSpec makeIv() {
		return makeIv(null, false);
	}

	public static AlgorithmParameterSpec makeIv(String str) {
		return makeIv(str, true);
	}

	public static AlgorithmParameterSpec makeIv(String str, boolean fail) {
		try {
			if (fail) {
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
		return makeKey(null, false);
	}

	public static Key makeKey(String str) {
		return makeKey(str, true);
	}

	public static Key makeKey(String str, boolean fail) {
		try {
			byte[] key = null;

			if (fail) {
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

	public static int makeIterationCount() {
		return rand(1000, 10000);
	}

	public static char[] makePassword() {
		return makePassword(rand(16, 64));
	}

	public static char[] makePassword(int length) {
		Random r = new SecureRandom();
		int size = ALPHABET.length();
		StringBuilder sb = new StringBuilder();
		for (int i = 0; i < length; i++) {
			int idx = r.nextInt(size);
			sb.append(ALPHABET.charAt(idx));
		}
		return sb.toString().toCharArray();
	}

	public static byte[] makeSalt() {
		byte[] salt = new byte[32];
		new SecureRandom().nextBytes(salt);
		return salt;
	}

	public static Key generatePBEKey(char[] password, byte[] salt, int iterationCount) throws NoSuchAlgorithmException, InvalidKeySpecException {
		String algo = "PBKDF2WithHmacSHA1";
		PBEKeySpec encPBESpec = new PBEKeySpec(password, salt, iterationCount, 64);
		SecretKeyFactory encKeyFact = SecretKeyFactory.getInstance(algo);
		return encKeyFact.generateSecret(encPBESpec);
	}

	public static byte[] encrypt(String text, Key key, AlgorithmParameterSpec iv) throws Exception {
		String alg = "AES/CBC/PKCS5Padding";
		Cipher cipher = Cipher.getInstance(alg);
		cipher.init(Cipher.ENCRYPT_MODE, key, iv);
		return cipher.doFinal(text.getBytes());
	}

	public static KeyPair generateKeyPair(int keySize) throws Exception {
		KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
		generator.initialize(keySize);
		return generator.generateKeyPair();
	}

	public static byte[] encrypt(String secretMessage, PublicKey publicKey) throws Exception {
		return encrypt(secretMessage, publicKey, "RSA");
	}

	public static byte[] encrypt(String secretMessage, PublicKey publicKey, String alg) throws Exception {
		Cipher encryptCipher = Cipher.getInstance(alg);
		encryptCipher.init(Cipher.ENCRYPT_MODE, publicKey);
		byte[] secretMessageBytes = secretMessage.getBytes(StandardCharsets.UTF_8);
		return encryptCipher.doFinal(secretMessageBytes);
	}

	public static byte[] decrypt(byte[] encryptedMessageBytes, PrivateKey privateKey) throws Exception {
		return decrypt(encryptedMessageBytes, privateKey, "RSA");
	}

	public static byte[] decrypt(byte[] encryptedMessageBytes, PrivateKey privateKey, String alg) throws Exception {
		Cipher decryptCipher = Cipher.getInstance(alg);
		decryptCipher.init(Cipher.DECRYPT_MODE, privateKey);
		return decryptCipher.doFinal(encryptedMessageBytes);
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
		if ((args != null && args.length == 1) && "true".equals(args[0].toLowerCase())) {
			fail = true;
		}
		return fail;
	}

	public static int rand(int min, int max) {
		Random random = new SecureRandom();
		return random.nextInt(max - min) + min;
	}
}
