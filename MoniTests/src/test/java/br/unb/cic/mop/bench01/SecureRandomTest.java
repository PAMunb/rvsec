package br.unb.cic.mop.bench01;

import br.unb.cic.mop.eh.ErrorCollector;
import br.unb.cic.misc.Assertions;
import br.unb.cic.mop.ExecutionContext;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

import java.security.NoSuchAlgorithmException;
import java.security.NoSuchProviderException;
import java.security.SecureRandom;

public class SecureRandomTest {
    @Before
    public void setUp() {
        ExecutionContext.instance().reset();
        ErrorCollector.instance().reset();
    }

    @After
    public void tearDown() {
        // ErrorCollector.instance().printErrors();
    }



    @Test
    public void secureRandomValidTest1() throws NoSuchAlgorithmException {
        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);
    }

    @Test
    public void secureRandomValidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {
        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG", "SUN");
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);
    }

    @Test
    public void secureRandomValidTest3() throws NoSuchAlgorithmException {
        SecureRandom secureRandom0 = SecureRandom.getInstanceStrong();
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);
    }

    @Test
    public void secureRandomValidTest4() {
        SecureRandom secureRandom0 = new SecureRandom();
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);
    }

    @Test
    public void secureRandomValidTest5() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom1 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom1.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom1);

        SecureRandom secureRandom0 = new SecureRandom(genSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest6() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom1 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom1.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom1);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        secureRandom0.setSeed(genSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest7() throws NoSuchAlgorithmException, NoSuchProviderException {

        int num = 0;

        SecureRandom secureRandom1 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom1.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom1);

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG", "SUN");
        secureRandom0.setSeed(genSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest8() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom1 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom1.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom1);

        SecureRandom secureRandom0 = SecureRandom.getInstanceStrong();
        secureRandom0.setSeed(genSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest9() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom1 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom1.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom1);

        SecureRandom secureRandom0 = new SecureRandom();
        secureRandom0.setSeed(genSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest10() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom1 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom1.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom1);

        SecureRandom secureRandom0 = new SecureRandom(genSeed);
        secureRandom0.setSeed(genSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest11() throws NoSuchAlgorithmException {

        long lSeed = 0;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        secureRandom0.setSeed(lSeed);
        Assertions.hasEnsuredPredicate(secureRandom0);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest12() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest13() throws NoSuchAlgorithmException, NoSuchProviderException {

        int num = 0;

        SecureRandom secureRandom0 = SecureRandom.getInstance("SHA1PRNG","SUN");
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

    @Test
    public void secureRandomValidTest14() throws NoSuchAlgorithmException {

        int num = 0;

        SecureRandom secureRandom0 = SecureRandom.getInstanceStrong();
        byte[] genSeed = secureRandom0.generateSeed(num);
        Assertions.hasEnsuredPredicate(genSeed);
        Assertions.mustBeInAcceptingState(secureRandom0);

    }

}
