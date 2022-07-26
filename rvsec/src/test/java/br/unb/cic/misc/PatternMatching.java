package br.unb.cic.misc;

import org.junit.Assert;
import org.junit.Test;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PatternMatching {

    @Test
    public void testFindClassName() {
        String location = "br.unb.cic.mop.bench02.brokenhash.BrokenHashABICase8.go(BrokenHashABICase8.java:25)";
        Pattern pattern = Pattern.compile("([\\w+\\.\\$]+)[.]([a-zA-Z]+)\\(.+\\)");
        Matcher matcher = pattern.matcher(location);
        Assert.assertTrue(matcher.matches());

        Assert.assertEquals("br.unb.cic.mop.bench02.brokenhash.BrokenHashABICase8", matcher.group(1));
    }

    @Test
    public void testFindMethod() {
        String location = "org.apache.directory.server.kerberos.shared.crypto.encryption.AesEncryptionTest.<clinit>(AesEncryptionTest.java:63)";
        Pattern pattern = Pattern.compile("([\\w+\\.\\$]+)[.](\\<?\\w+\\>?)\\((.+)\\)");
        Matcher matcher = pattern.matcher(location);
        Assert.assertTrue(matcher.matches());

        Assert.assertEquals("org.apache.directory.server.kerberos.shared.crypto.encryption.AesEncryptionTest", matcher.group(1));
        Assert.assertEquals("<clinit>", matcher.group(2));
        Assert.assertEquals("AesEncryptionTest.java:63", matcher.group(3));
    }
}
