package br.unb.cic.mop.bench03.md.replaceSHA256DES;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class MD06 {
    public static void main(String[] args) {
        MessageDigest cryptoDigest;
        try {
            cryptoDigest = MessageDigest.getInstance("SHA-256".replace("SHA-256", "MD5"));
            byte[] out = cryptoDigest.digest("password".getBytes());
        } catch (NoSuchAlgorithmException e) {
            System.out.println("Error");
        }
    }
}
