package br.unb.cic.cryptoapp.generated;

import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Utility class for cryptographic operations.
 * This class provides helper methods for encryption, decryption, hashing, and other
 * cryptographic operations used in the CryptographyActivity.
 */
public class CryptoUtils {

    /**
     * Generates a secret key using the specified algorithm and key size.
     *
     * @param algorithm The algorithm to use for key generation
     * @return The generated secret key
     * @throws NoSuchAlgorithmException If the algorithm is not available
     */
    public static SecretKey generateSecretKey(String algorithm) throws Exception {
        int keySize;

        // Determine key size based on algorithm
        switch (algorithm) {
            case "AES":
                keySize = 128; // AES-128
                break;
            case "DES":
                keySize = 56;
                break;
            case "TripleDES":
                keySize = 168;
                break;
            case "Blowfish":
                keySize = 128;
                break;
            case "RC4":
                keySize = 128;
                break;
            default:
                keySize = 128;
        }

        // Generate key
        KeyGenerator keyGen = KeyGenerator.getInstance(algorithm);
        keyGen.init(keySize);
        return keyGen.generateKey();
    }

    /**
     * Generates a new initialization vector (IV) for use with block ciphers.
     *
     * @param size The size of the IV in bytes
     * @return A byte array containing the generated IV
     */
    public static byte[] generateIV(int size) {
        SecureRandom random = new SecureRandom();
        byte[] iv = new byte[size];
        random.nextBytes(iv);
        return iv;
    }

    /**
     * Encrypts data using a secret key.
     *
     * @param data The data to encrypt
     * @param secretKey The secret key to use for encryption
     * @param algorithm The encryption algorithm
     * @param iv The initialization vector (may be null for some algorithms)
     * @return The encrypted data
     * @throws Exception If an error occurs during encryption
     */
    public static byte[] encryptWithSecretKey(byte[] data, SecretKey secretKey, String algorithm, byte[] iv) throws Exception {
        Cipher cipher;

        // Initialize cipher based on algorithm
        if (algorithm.equals("AES") || algorithm.equals("TripleDES")) {
            // Block ciphers that need an IV
            String transformation = algorithm + "/CBC/PKCS5Padding";
            cipher = Cipher.getInstance(transformation);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, new IvParameterSpec(iv));
        } else {
            // Stream ciphers or other block ciphers
            cipher = Cipher.getInstance(algorithm);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);
        }

        // Encrypt
        return cipher.doFinal(data);
    }

    /**
     * Decrypts data using a secret key.
     *
     * @param encryptedData The data to decrypt
     * @param secretKey The secret key to use for decryption
     * @param algorithm The decryption algorithm
     * @param iv The initialization vector (may be null for some algorithms)
     * @return The decrypted data
     * @throws Exception If an error occurs during decryption
     */
    public static byte[] decryptWithSecretKey(byte[] encryptedData, SecretKey secretKey, String algorithm, byte[] iv) throws Exception {
        Cipher cipher;

        // Initialize cipher based on algorithm
        if (algorithm.equals("AES") || algorithm.equals("TripleDES")) {
            // Block ciphers that need an IV
            String transformation = algorithm + "/CBC/PKCS5Padding";
            cipher = Cipher.getInstance(transformation);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, new IvParameterSpec(iv));
        } else {
            // Stream ciphers or other block ciphers
            cipher = Cipher.getInstance(algorithm);
            cipher.init(Cipher.DECRYPT_MODE, secretKey);
        }

        // Decrypt
        return cipher.doFinal(encryptedData);
    }

    /**
     * Generates a key pair using the specified algorithm.
     *
     * @param algorithm The algorithm to use for key pair generation
     * @return The generated key pair
     * @throws Exception If an error occurs during key pair generation
     */
    public static KeyPair generateKeyPair(String algorithm) throws Exception {
        int keySize;

        // Determine key size based on algorithm
        switch (algorithm) {
            case "RSA":
                keySize = 2048;
                break;
            case "DSA":
                keySize = 1024;
                break;
            case "EC":
                keySize = 256;
                break;
            case "DiffieHellman":
                keySize = 2048;
                break;
            default:
                keySize = 2048;
        }

        // Generate key pair
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance(algorithm);
        keyGen.initialize(keySize);
        return keyGen.generateKeyPair();
    }

    /**
     * Encrypts data using a public key.
     *
     * @param data The data to encrypt
     * @param publicKey The public key to use for encryption
     * @param algorithm The encryption algorithm
     * @return The encrypted data
     * @throws Exception If an error occurs during encryption
     */
    public static byte[] encryptWithPublicKey(byte[] data, PublicKey publicKey, String algorithm) throws Exception {
        // For RSA, use PKCS1Padding
        String transformation = algorithm + "/ECB/PKCS1Padding";
        Cipher cipher = Cipher.getInstance(transformation);
        cipher.init(Cipher.ENCRYPT_MODE, publicKey);
        return cipher.doFinal(data);
    }

    /**
     * Decrypts data using a private key.
     *
     * @param encryptedData The data to decrypt
     * @param privateKey The private key to use for decryption
     * @param algorithm The decryption algorithm
     * @return The decrypted data
     * @throws Exception If an error occurs during decryption
     */
    public static byte[] decryptWithPrivateKey(byte[] encryptedData, PrivateKey privateKey, String algorithm) throws Exception {
        // For RSA, use PKCS1Padding
        String transformation = algorithm + "/ECB/PKCS1Padding";
        Cipher cipher = Cipher.getInstance(transformation);
        cipher.init(Cipher.DECRYPT_MODE, privateKey);
        return cipher.doFinal(encryptedData);
    }

    /**
     * Computes a hash of the specified data using the specified algorithm.
     *
     * @param data The data to hash
     * @param algorithm The hashing algorithm
     * @return The hash value
     * @throws NoSuchAlgorithmException If the algorithm is not available
     */
    public static byte[] computeHash(byte[] data, String algorithm) throws NoSuchAlgorithmException {
        MessageDigest md = MessageDigest.getInstance(algorithm);
        return md.digest(data);
    }

    /**
     * Computes an HMAC of the specified data using the specified algorithm and key.
     *
     * @param data The data to compute the HMAC for
     * @param secretKey The secret key to use
     * @param algorithm The HMAC algorithm
     * @return The HMAC value
     * @throws Exception If an error occurs during HMAC computation
     */
    public static byte[] computeHmac(byte[] data, SecretKey secretKey, String algorithm) throws Exception {
        Mac mac = Mac.getInstance(algorithm);
        mac.init(secretKey);
        return mac.doFinal(data);
    }

    /**
     * Converts a byte array to a hexadecimal string.
     *
     * @param bytes The byte array to convert
     * @return The hexadecimal representation of the byte array
     */
    public static String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }

    /**
     * Creates a secret key from a byte array.
     *
     * @param keyBytes The key bytes
     * @param algorithm The algorithm
     * @return The secret key
     */
    public static SecretKey createSecretKeyFromBytes(byte[] keyBytes, String algorithm) {
        return new SecretKeySpec(keyBytes, algorithm);
    }
}
