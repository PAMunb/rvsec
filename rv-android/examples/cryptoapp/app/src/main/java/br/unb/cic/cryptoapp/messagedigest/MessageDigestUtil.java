package br.unb.cic.cryptoapp.messagedigest;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import static br.unb.cic.cryptoapp.util.Utils.*;

public class MessageDigestUtil {

    public String hash(String input, String algorithm) {
        return hash(input.getBytes(), algorithm);
    }

    public String hash(byte[] input, String algorithm) {
        String digestResult = "";
        try {
            MessageDigest messageDigest = MessageDigest.getInstance(algorithm);
            messageDigest.update(input);
            byte[] digest = messageDigest.digest();
            digestResult = bytesToHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("No such algorithm: " + e.getMessage(), e);
        } catch (Exception e) {
            throw new RuntimeException("MessageDigest error: " + e.getMessage(), e);
        }
        return digestResult;
    }

    public String unreachableHash(String input) {
        return hash(input.getBytes(), "MD5");
    }

}
