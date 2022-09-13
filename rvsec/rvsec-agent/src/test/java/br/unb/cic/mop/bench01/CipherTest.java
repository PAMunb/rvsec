package br.unb.cic.mop.bench01;

import org.junit.Ignore;
import org.junit.Test;

import br.unb.cic.misc.Assertions;

import javax.crypto.*;
import javax.crypto.spec.DHGenParameterSpec;
import javax.crypto.spec.GCMParameterSpec;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.security.*;
import java.security.cert.Certificate;
import java.security.spec.InvalidParameterSpecException;

public class CipherTest {

    private Certificate loadCertificate() throws Exception {
        File ksInputFile = new File(getClass().getClassLoader().getResource("testInput-ks").getFile());
        InputStream fileIn = new FileInputStream(ksInputFile);
        KeyStore keyStore0 = KeyStore.getInstance("JKS");
        keyStore0.load(fileIn, "password".toCharArray());
        return keyStore0.getCertificate("certificate01");
    }


    @Ignore("We could not fix test cases using WRAP and RSA.")
    public void cipherValidTest1() throws Exception {

        Certificate cert = loadCertificate();

        Key wrappedKey = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(Cipher.WRAP_MODE, cert);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using WRAP and RSA.")
    public void cipherValidTest2() throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidKeyException, NoSuchProviderException {

        Certificate cert = null;
        Key wrappedKey = null;

        Cipher cipher0 = Cipher.getInstance("RSA", (String) null);
        cipher0.init(1, cert);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using WRAP and RSA.")
    public void cipherValidTest3()
            throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Certificate cert = null;
        Key wrappedKey = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert, secureRandom0);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest4()
            throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        Key wrappedKey = KeyGenerator.getInstance("AES").generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher0.init(Cipher.WRAP_MODE, secretKey);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest5()
            throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Key wrappedKey = KeyGenerator.getInstance("AES").generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/CBC/PKCS5Padding");

        cipher0.init(Cipher.WRAP_MODE, secretKey, secureRandom0);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest6() throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        Key wrappedKey = KeyGenerator.getInstance("AES").generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");

        cipher0.init(Cipher.WRAP_MODE, secretKey, gCMParameterSpec0);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using DHGenParameterSpec.")
    public void cipherValidTest7() throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        Key wrappedKey = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest8() throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        Key wrappedKey = KeyGenerator.getInstance("AES").generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(Cipher.WRAP_MODE, secretKey, gCMParameterSpec0, secureRandom0);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using DHGenParameterSpec.")
    public void cipherValidTest9() throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Key wrappedKey = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0, secureRandom0);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest10() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest11() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA", "SunJCE");
        cipher0.init(1, cert);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest12() throws Exception {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert, secureRandom0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }



    //TODO: This test case is not correct. There are a couple of mistakes.
    //  - we cannot use RSA with an AES key
    //  - we cannot call wrap using the DECRYPT_MODE (only WRAP_MODE). See the call cipher0.init(1, secretKey);
    //  - wrappedKey must not be null
    @Ignore
    public void wrongTestCase()
            throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        Key wrappedKey = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest13()
            throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        Key wrappedKey = keyGenerator0.generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher0.init(Cipher.WRAP_MODE, secretKey);
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.hasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest14() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/CBC/PKCS5Padding");
        cipher0.init(1, secretKey, secureRandom0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest15() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;// 0 leads to an empty genSeed... so we changed it.

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using DHGenParameterSpec.")
    public void cipherValidTest16()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        byte[] plainText = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest17() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2022;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0, secureRandom0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using DHGenParameterSpec.")
    public void cipherValidTest18()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        byte[] plainText = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0, secureRandom0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest19() throws Exception {
        Certificate cert = loadCertificate();

        int plain_off = 0;
        byte[] plainText = "secret".getBytes();
        int len = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] cipherText = cipher0.doFinal(plainText, plain_off, len);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest20() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();
        byte[] cipherText = new byte[512];

        int plain_off = 0;
        int len = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.doFinal(plainText, plain_off, len, cipherText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest21() throws Exception {

        Certificate cert = loadCertificate();

        byte[] cipherText = new byte[512];
        byte[] plainText = "secret".getBytes();

        int plain_off = 0;
        int len = 0;
        int ciphertext_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.doFinal(plainText, plain_off, len, cipherText, ciphertext_off);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest22() throws Exception {

        Certificate cert = loadCertificate();

        ByteBuffer plainBuffer = ByteBuffer.allocate(20);
        ByteBuffer cipherBuffer = ByteBuffer.allocate(512);

        plainBuffer.put("secret".getBytes());

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.doFinal(plainBuffer, cipherBuffer);
        Assertions.hasEnsuredPredicate(cipherBuffer);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest23() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText =  "secret".getBytes();
        byte[] pre_plaintext = "pre-plaintext".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest24() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText =  "secret".getBytes();
        byte[] pre_plaintext = "pre-plaintext".getBytes();


        Cipher cipher0 = Cipher.getInstance("RSA", "SunJCE");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest25() throws Exception {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest26() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest27() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest28() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2022;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using DHGenParameterSpec.")
    public void cipherValidTest29()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        byte[] plainText = null;
        byte[] pre_plaintext = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest30() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2022;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Ignore("We could not fix test cases using DHGenParameterSpec.")
    public void cipherValidTest31()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        byte[] plainText = null;
        byte[] pre_plaintext = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest32() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext, pre_plain_off, 0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest33() throws Exception {

        Certificate cert = loadCertificate();
        int pre_len = 0;
        byte[] plainText = "secret".getBytes();
        byte[] pre_ciphertext = "pre-cipher-text".getBytes();
        byte[] pre_plaintext = "pre-plain-text".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.update(pre_plaintext, pre_plain_off, pre_len, pre_ciphertext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest34() throws Exception {

        int pre_ciphertext_off = 0;
        Certificate cert = loadCertificate();
        int pre_len = 0;
        byte[] plainText = "secret".getBytes();
        byte[] pre_ciphertext = "pre-cipher-text".getBytes();
        byte[] pre_plaintext = "pre-plain-text".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.update(pre_plaintext, pre_plain_off, pre_len, pre_ciphertext, pre_ciphertext_off);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest35() throws Exception {

        Certificate cert = loadCertificate();
        byte[] plainText = "secret".getBytes();
        ByteBuffer pre_plainBuffer = ByteBuffer.allocate(256);
        ByteBuffer pre_cipherBuffer = ByteBuffer.allocate(1024);

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.update(pre_plainBuffer, pre_cipherBuffer);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest36() throws Exception {

        Certificate cert = loadCertificate();

        int plain_off = 0;
        int len = 0;

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText, plain_off, len);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest37() throws Exception {

        Certificate cert = loadCertificate();

        int plain_off = 0;
        int len = 0;

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();
        byte[] cipherText = new byte[512];

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(plainText, plain_off, len, cipherText);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest38() throws Exception {

        Certificate cert = loadCertificate();

        int plain_off = 0;
        int len = 0;
        int ciphertext_off = 0;

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();
        byte[] cipherText = new byte[512];


        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(plainText, plain_off, len, cipherText, ciphertext_off);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest39() throws Exception {

        Certificate cert = loadCertificate();

        ByteBuffer plainBuffer = ByteBuffer.allocate(256);
        ByteBuffer cipherBuffer = ByteBuffer.allocate(512);

        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(plainBuffer, cipherBuffer);
        Assertions.hasEnsuredPredicate(cipherBuffer);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest40() throws Exception {

        Certificate cert = loadCertificate();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal();
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherValidTest41() throws Exception {

        Certificate cert = loadCertificate();

        byte[] pre_plaintext = "pre-plain".getBytes();
        byte[] cipherText = new byte[512];

        int ciphertext_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(cipherText, ciphertext_off);
        Assertions.hasEnsuredPredicate(cipherText);
        Assertions.mustBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest1() throws NoSuchPaddingException, NoSuchAlgorithmException {

        Cipher cipher0 = Cipher.getInstance("RSA");
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest2() throws NoSuchPaddingException, NoSuchAlgorithmException, NoSuchProviderException {

        Cipher cipher0 = Cipher.getInstance("RSA", "SunJCE");
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest3() throws Exception {

        Certificate cert = loadCertificate();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest4() throws Exception {

        Certificate cert = loadCertificate();

        Cipher cipher0 = Cipher.getInstance("RSA", "SunJCE");
        cipher0.init(1, cert);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest5() throws Exception {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Certificate cert = loadCertificate();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert, secureRandom0);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest6() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest7() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, secureRandom0);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest8() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException,
            InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Ignore
    public void cipherInvalidTest9() throws NoSuchPaddingException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest10() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException,
            InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0, secureRandom0);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Ignore
    public void cipherInvalidTest11() throws NoSuchPaddingException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0, secureRandom0);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest12()
            throws NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException, InvalidKeyException {

        Key wrappedKey = KeyGenerator.getInstance("AES").generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding"); // changed the argument from RSA to AES/GCM/NoPadding
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.notHasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest13() throws NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, InvalidKeyException, NoSuchProviderException {

        Key wrappedKey = KeyGenerator.getInstance("AES").generateKey();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding", "SunJCE");
        byte[] wrappedKeyBytes = cipher0.wrap(wrappedKey);
        Assertions.notHasEnsuredPredicate(wrappedKeyBytes);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest14()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException {

        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest15() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, NoSuchProviderException {

        byte[] plainText = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding", "SunJCE");
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest16()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException {

        int plain_off = 0;
        byte[] plainText = "secret".getBytes();
        int len = 256;

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        byte[] cipherText = cipher0.doFinal(plainText, plain_off, len);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest17() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        byte[] cipherText = new byte[512];
        int plain_off = 0;
        byte[] plainText = "secret".getBytes();
        int len = 0;

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.doFinal(plainText, plain_off, len, cipherText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest18() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        byte[] cipherText = new byte[512];
        int plain_off = 0;
        byte[] plainText = "secret".getBytes();
        int len = 0;
        int ciphertext_off = 0;

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.doFinal(plainText, plain_off, len, cipherText, ciphertext_off);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest19() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        ByteBuffer plainBuffer = ByteBuffer.allocate(512);
        ByteBuffer cipherBuffer = ByteBuffer.allocate(512);

        plainBuffer.put("secret".getBytes());

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.doFinal(plainBuffer, cipherBuffer);
        Assertions.notHasEnsuredPredicate(cipherBuffer);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest20() throws Exception {

        Certificate cert = loadCertificate();

        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest21() throws Exception {

        Certificate cert = loadCertificate();
        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA", "SunJCE");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest22() throws Exception {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        Certificate cert = loadCertificate();
        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest23() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest24() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest25() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException,
            InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Ignore
    public void cipherInvalidTest26() throws NoSuchPaddingException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        byte[] pre_plaintext = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest27() throws NoSuchPaddingException, NoSuchAlgorithmException, InvalidKeyException,
            InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int num = 2024;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

        GCMParameterSpec gCMParameterSpec0 = new GCMParameterSpec(96, genSeed);
        Assertions.hasEnsuredPredicate(gCMParameterSpec0);
        Assertions.mustBeInAcceptingState(gCMParameterSpec0);

        byte[] pre_plaintext = "secret".getBytes();

        Cipher cipher0 = Cipher.getInstance("AES/GCM/NoPadding");
        cipher0.init(1, secretKey, gCMParameterSpec0, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Ignore
    public void cipherInvalidTest28() throws NoSuchPaddingException, NoSuchAlgorithmException,
            InvalidParameterSpecException, InvalidKeyException, InvalidAlgorithmParameterException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

        int exponentSize = 0;
        int primeSize = 0;

        DHGenParameterSpec dHGenParameterSpec0 = new DHGenParameterSpec(primeSize, exponentSize);
        Assertions.hasEnsuredPredicate(dHGenParameterSpec0);
        Assertions.mustBeInAcceptingState(dHGenParameterSpec0);

        AlgorithmParameters algorithmParameters0 = AlgorithmParameters.getInstance("AES");
        algorithmParameters0.init(dHGenParameterSpec0);
        Assertions.hasEnsuredPredicate(algorithmParameters0);
        Assertions.mustBeInAcceptingState(algorithmParameters0);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        byte[] pre_plaintext = null;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, secretKey, algorithmParameters0, secureRandom0);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest29() throws Exception {

        Certificate cert = loadCertificate();
        byte[] pre_plaintext = "secret".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        byte[] pre_ciphertext = cipher0.update(pre_plaintext, pre_plain_off, 0);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest30() throws  Exception {

        Certificate cert = loadCertificate();
        int pre_len = 0;
        byte[] pre_ciphertext = new byte[512];
        byte[] pre_plaintext = "secret".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.update(pre_plaintext, pre_plain_off, pre_len, pre_ciphertext);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest31() throws Exception {

        int pre_ciphertext_off = 0;
        Certificate cert = loadCertificate();
        int pre_len = 0;
        byte[] pre_ciphertext = new byte[512];
        byte[] pre_plaintext = "secret".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.update(pre_plaintext, pre_plain_off, pre_len, pre_ciphertext, pre_ciphertext_off);
        Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test
    public void cipherInvalidTest32() throws Exception {

        Certificate cert = loadCertificate();

        ByteBuffer pre_plainBuffer = ByteBuffer.allocate(512);
        ByteBuffer pre_cipherBuffer = ByteBuffer.allocate(512);;

        pre_plainBuffer.put("secret".getBytes());

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.init(1, cert);
        cipher0.update(pre_plainBuffer, pre_cipherBuffer);
        Assertions.hasEnsuredPredicate(pre_cipherBuffer);   // TODO: I had to fix this: Assertions.hasEnsuredPredicate(pre_ciphertext);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest33()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException {

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest34() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, NoSuchProviderException {

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA", "SunJCE");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest35()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException {

        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();
        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext, pre_plain_off, 0);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest36() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        int pre_len = 0;
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();
        byte[] pre_ciphertext = new byte[512];

        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.update(pre_plaintext, pre_plain_off, pre_len, pre_ciphertext);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest37() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        int pre_ciphertext_off = 0;
        int pre_len = 0;
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();
        byte[] pre_ciphertext = new byte[512];

        int pre_plain_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.update(pre_plaintext, pre_plain_off, pre_len, pre_ciphertext, pre_ciphertext_off);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest38() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        ByteBuffer pre_plainBuffer = ByteBuffer.allocate(512);
        byte[] plainText = "secret".getBytes();
        ByteBuffer pre_cipherBuffer = ByteBuffer.allocate(512);

        Cipher cipher0 = Cipher.getInstance("RSA");
        cipher0.update(pre_plainBuffer, pre_cipherBuffer);
        byte[] cipherText = cipher0.doFinal(plainText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest39()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException {

        int plain_off = 0;
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        int len = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal(plainText, plain_off, len);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest40() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        byte[] cipherText = new byte[512];
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        int plain_off = 0;
        int len = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(plainText, plain_off, len, cipherText);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest41() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        byte[] cipherText = new byte[512];
        byte[] plainText = "secret".getBytes();
        byte[] pre_plaintext = "pre-plain".getBytes();

        int plain_off = 0;
        int len = 0;

        int ciphertext_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(plainText, plain_off, len, cipherText, ciphertext_off);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest42() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        ByteBuffer plainBuffer = ByteBuffer.allocate(512);
        ByteBuffer cipherBuffer = ByteBuffer.allocate(512);

        plainBuffer.put("secret".getBytes());
        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(plainBuffer, cipherBuffer);
        Assertions.notHasEnsuredPredicate(cipherBuffer);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest43()
            throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException, NoSuchAlgorithmException {

        byte[] pre_plaintext = "pre-plain".getBytes();

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        byte[] cipherText = cipher0.doFinal();
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }

    @Test(expected = java.lang.IllegalStateException.class)
    public void cipherInvalidTest44() throws BadPaddingException, NoSuchPaddingException, IllegalBlockSizeException,
            NoSuchAlgorithmException, ShortBufferException {

        byte[] cipherText = new byte[512];
        byte[] pre_plaintext = "pre-plain".getBytes();
        int ciphertext_off = 0;

        Cipher cipher0 = Cipher.getInstance("RSA");
        byte[] pre_ciphertext = cipher0.update(pre_plaintext);
        cipher0.doFinal(cipherText, ciphertext_off);
        Assertions.notHasEnsuredPredicate(cipherText);
        Assertions.mustNotBeInAcceptingState(cipher0);

    }
}
