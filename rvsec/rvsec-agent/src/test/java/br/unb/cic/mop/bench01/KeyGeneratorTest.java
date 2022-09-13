package br.unb.cic.mop.bench01;

import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.misc.Assertions;
import br.unb.cic.mop.ExecutionContext;

import org.junit.Before;
import org.junit.Test;

import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import java.security.*;
import java.security.spec.AlgorithmParameterSpec;

public class KeyGeneratorTest {
    @Before
    public void setUp() {
        ErrorCollector.instance().reset();
    }


    @Test
    public void safeAlgorithmWithoutSpecifiedProvider() throws Exception {
        KeyGenerator generator = KeyGenerator.getInstance("AES");
        generator.init(192);
        SecretKey key = generator.generateKey();
        Assertions.expectingEmptySetOfErrors();
        Assertions.hasEnsuredPredicate(ExecutionContext.Property.GENERATED_KEY, key);
    }

    @Test
    public void unsafeAlgorithmWithoutSpecifiedProvider() throws Exception {
        SecureRandom random = new SecureRandom();
        KeyGenerator generator = KeyGenerator.getInstance("DES");
        generator.init(56);
        generator.generateKey();
        Assertions.expectingNonEmptySetOfErrors();
    }

    @Test
    public void keyGeneratorValidTest1() throws NoSuchAlgorithmException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorValidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES", "SunJCE");
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorValidTest3() throws NoSuchAlgorithmException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(128);
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorValidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES", "SunJCE");
        keyGenerator0.init(128);
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorValidTest5() throws NoSuchAlgorithmException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(128, secureRandom0);
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test(expected = java.security.InvalidAlgorithmParameterException.class)
    public void keyGeneratorValidTest6() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

        AlgorithmParameterSpec params = null;

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(params);
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test(expected = java.security.InvalidAlgorithmParameterException.class)
    public void keyGeneratorValidTest7() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        AlgorithmParameterSpec params = null;

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(params, secureRandom0);
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorValidTest8() throws NoSuchAlgorithmException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(secureRandom0);
        SecretKey secretKey = keyGenerator0.generateKey();
        Assertions.hasEnsuredPredicate(secretKey);
        Assertions.mustBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorInvalidTest1() throws NoSuchAlgorithmException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorInvalidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES", "SunJCE");
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorInvalidTest3() throws NoSuchAlgorithmException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(128);
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorInvalidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES", "SunJCE");
        keyGenerator0.init(128);
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorInvalidTest5() throws NoSuchAlgorithmException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(128, secureRandom0);
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test(expected = java.security.InvalidAlgorithmParameterException.class)
    public void keyGeneratorInvalidTest6() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

        AlgorithmParameterSpec params = null;

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(params);
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test(expected = java.security.InvalidAlgorithmParameterException.class)
    public void keyGeneratorInvalidTest7() throws NoSuchAlgorithmException, InvalidAlgorithmParameterException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        AlgorithmParameterSpec params = null;

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(params, secureRandom0);
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }

    @Test
    public void keyGeneratorInvalidTest8() throws NoSuchAlgorithmException {

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

        KeyGenerator keyGenerator0 = KeyGenerator.getInstance("AES");
        keyGenerator0.init(secureRandom0);
        Assertions.mustNotBeInAcceptingState(keyGenerator0);

    }
}