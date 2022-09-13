package br.unb.cic.mop.bench03.md.baseCase;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class MD01 {

    public static void main(String[] args) {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("MD5");
            byte[] out = digest.digest("password".getBytes());
        } catch (NoSuchAlgorithmException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }
}
