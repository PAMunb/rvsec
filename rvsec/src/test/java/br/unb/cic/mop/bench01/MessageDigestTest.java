package br.unb.cic.mop.bench01;

import java.nio.ByteBuffer;
import java.security.DigestException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.NoSuchProviderException;

import org.junit.Ignore;
import org.junit.Test;

import br.unb.cic.misc.Assertions;

public class MessageDigestTest  {

    @Test
    public void messageDigestValidTest1() throws NoSuchAlgorithmException {

        byte[] inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

        byte[] inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256", "SUN");
        byte[] out = messageDigest0.digest(inbytearr);
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest3() throws NoSuchAlgorithmException {

        byte[] inbytearr = "secret".getBytes();
        byte pre_inbyte = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inbyte);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {

        byte[] inbytearr = "secret".getBytes();
        byte pre_inbyte = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256", "SUN");
        byte[] out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inbyte);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest5() throws NoSuchAlgorithmException {

        byte[] pre_inbytearr = "secret1".getBytes();
        byte[] inbytearr = "secret2".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inbytearr);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest6() throws NoSuchAlgorithmException {

        byte[] pre_inbytearr = "secret1".getBytes();
        int pre_off = 0;
        byte[] inbytearr = "secret2".getBytes();
        int pre_len = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inbytearr, pre_off, pre_len);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest7() throws NoSuchAlgorithmException {

        byte[] inbytearr = "secret".getBytes();
        ByteBuffer pre_inpBuf = ByteBuffer.allocate(20);

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inpBuf);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestValidTest8() throws NoSuchAlgorithmException, DigestException {

        int off = 0;
        byte[] inbytearr = "secret".getBytes();
        byte pre_inbyte = 0;
        int len = 32;
        byte[] out = new byte[256];

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inbyte);
        messageDigest0.digest(out, off, len);
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestValidTest9() throws NoSuchAlgorithmException {

        byte[] inbytearr = "secret".getBytes();
        byte pre_inbyte = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        messageDigest0.update(pre_inbyte);
        out = messageDigest0.digest(inbytearr);
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestInvalidTest1() throws NoSuchAlgorithmException {

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestInvalidTest2() throws NoSuchAlgorithmException, NoSuchProviderException {

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256", "SUN");
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest3() throws NoSuchAlgorithmException {

        byte pre_inbyte = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        messageDigest0.update(pre_inbyte);
        byte[] out = messageDigest0.digest();
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest4() throws NoSuchAlgorithmException, NoSuchProviderException {

        byte pre_inbyte = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256", "SUN");
        messageDigest0.update(pre_inbyte);
        byte[] out = messageDigest0.digest();
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest5() throws NoSuchAlgorithmException {

        byte[] pre_inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        messageDigest0.update(pre_inbytearr);
        byte[] out = messageDigest0.digest();
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest6() throws NoSuchAlgorithmException {

        byte[] pre_inbytearr = "secret".getBytes();
        int pre_off = 0;
        int pre_len = 0;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        messageDigest0.update(pre_inbytearr, pre_off, pre_len);
        byte[] out = messageDigest0.digest();
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest7() throws NoSuchAlgorithmException {

        ByteBuffer pre_inpBuf = ByteBuffer.allocate(40);

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        messageDigest0.update(pre_inpBuf);
        byte[] out = messageDigest0.digest();
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest8() throws NoSuchAlgorithmException, DigestException {

        int off = 0;
        byte pre_inbyte = 0;
        int len = 32;
        byte[] out = new byte[40];

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        messageDigest0.update(pre_inbyte);
        messageDigest0.digest(out, off, len);
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest9() throws NoSuchAlgorithmException {

        byte pre_inbyte = 0;
        byte[] inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        messageDigest0.update(pre_inbyte);
        byte[] out = messageDigest0.digest(inbytearr);
        Assertions.notHasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestInvalidTest10() throws NoSuchAlgorithmException {

        byte[] inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestInvalidTest11() throws NoSuchAlgorithmException, NoSuchProviderException {

        byte[] inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256", "SUN");
        byte[] out = messageDigest0.digest(inbytearr);
        out = messageDigest0.digest();
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Test
    public void messageDigestInvalidTest12() throws NoSuchAlgorithmException, DigestException {

        int off = 0;
        byte[] inbytearr = "secret".getBytes();
        int len = 32;
        byte[] out = null;

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        out = messageDigest0.digest(inbytearr);
        messageDigest0.digest(out, off, len);
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }

    @Ignore
    public void messageDigestInvalidTest13() throws NoSuchAlgorithmException {

        byte[] inbytearr = "secret".getBytes();

        MessageDigest messageDigest0 = MessageDigest.getInstance("SHA-256");
        byte[] out = messageDigest0.digest(inbytearr);
        out = messageDigest0.digest(inbytearr);
        Assertions.hasEnsuredPredicate(out);
        Assertions.mustNotBeInAcceptingState(messageDigest0);

    }
}
