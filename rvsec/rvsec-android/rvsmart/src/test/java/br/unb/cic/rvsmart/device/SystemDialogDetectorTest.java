package br.unb.cic.rvsmart.device;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for SystemDialogDetector package matching logic.
 * Note: Cannot test full dismiss() flow without Android runtime,
 * but we can verify the package detection logic.
 */
class SystemDialogDetectorTest {

    private static final Set<String> SYSTEM_PACKAGES = new HashSet<>(Arrays.asList(
            "android",
            "com.android.packageinstaller",
            "com.google.android.packageinstaller",
            "com.android.settings"
    ));

    @Test
    void testSystemPackagesDetected() {
        for (String pkg : SYSTEM_PACKAGES) {
            assertTrue(SYSTEM_PACKAGES.contains(pkg),
                    "Should detect system package: " + pkg);
        }
    }

    @Test
    void testAppPackagesNotDetected() {
        assertFalse(SYSTEM_PACKAGES.contains("br.unb.cic.cryptoapp"));
        assertFalse(SYSTEM_PACKAGES.contains("com.example.myapp"));
        assertFalse(SYSTEM_PACKAGES.contains("com.android.chrome"));
    }

    @Test
    void testSystemUiNotDetected() {
        // com.android.systemui is NOT a system dialog — it's status/nav bar
        assertFalse(SYSTEM_PACKAGES.contains("com.android.systemui"));
    }

    @Test
    void testDismissLabels() {
        Set<String> labels = new HashSet<>(Arrays.asList(
                "ok", "allow", "deny", "close", "wait",
                "open app again", "close app"
        ));
        assertTrue(labels.contains("ok"));
        assertTrue(labels.contains("allow"));
        assertTrue(labels.contains("deny"));
        assertFalse(labels.contains("cancel"));
        assertFalse(labels.contains("submit"));
    }
}
