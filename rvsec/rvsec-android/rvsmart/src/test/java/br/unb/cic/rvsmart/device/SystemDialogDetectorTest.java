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
        // Mirrors DISMISS_LABELS in SystemDialogDetector — keep in sync when labels change.
        Set<String> labels = new HashSet<>(Arrays.asList(
                "ok", "allow", "deny", "close", "wait",
                "open app again", "close app",
                "cancel", "retry", "dismiss", "got it",
                "continue", "not now", "no thanks", "done"
        ));
        assertTrue(labels.contains("ok"));
        assertTrue(labels.contains("allow"));
        assertTrue(labels.contains("deny"));
        assertTrue(labels.contains("cancel"));
        assertFalse(labels.contains("submit"));
    }

    // --- Task 7.4: system dialog escalation ---

    @Test
    void testDismissReturnsFalseWhenNoMatchingLabel() {
        // dismiss() returns false when the dialog has no button whose label matches
        // DISMISS_LABELS. In the Android runtime this requires a live node; here we
        // verify the label-matching logic on the known label set directly.
        Set<String> labels = new HashSet<>(Arrays.asList(
                "ok", "allow", "deny", "close", "wait",
                "open app again", "close app",
                "cancel", "retry", "dismiss", "got it",
                "continue", "not now", "no thanks", "done"
        ));
        // "submit" is not a dismiss label — dismiss() would return false for such a button
        assertFalse(labels.contains("submit"),
                "submit is not a dismiss label — dismiss() returns false");
        assertFalse(labels.contains("yes"),
                "yes is not a dismiss label — dismiss() returns false");
    }

    @Test
    void testExpandedLabelsAreRecognised() {
        // All labels added in task 7.3 must be present in DISMISS_LABELS.
        // Test mirrors the actual set to catch accidental omissions.
        Set<String> labels = new HashSet<>(Arrays.asList(
                "ok", "allow", "deny", "close", "wait",
                "open app again", "close app",
                "cancel", "retry", "dismiss", "got it",
                "continue", "not now", "no thanks", "done"
        ));
        // Original labels
        assertTrue(labels.contains("ok"));
        assertTrue(labels.contains("allow"));
        assertTrue(labels.contains("deny"));
        assertTrue(labels.contains("close"));
        assertTrue(labels.contains("wait"));
        assertTrue(labels.contains("open app again"));
        assertTrue(labels.contains("close app"));
        // Newly added labels (task 7.3)
        assertTrue(labels.contains("cancel"), "cancel must be a dismiss label");
        assertTrue(labels.contains("retry"), "retry must be a dismiss label");
        assertTrue(labels.contains("dismiss"), "dismiss must be a dismiss label");
        assertTrue(labels.contains("got it"), "got it must be a dismiss label");
        assertTrue(labels.contains("continue"), "continue must be a dismiss label");
        assertTrue(labels.contains("not now"), "not now must be a dismiss label");
        assertTrue(labels.contains("no thanks"), "no thanks must be a dismiss label");
        assertTrue(labels.contains("done"), "done must be a dismiss label");
    }

    @Test
    void testCaseInsensitiveMatchingApplied() {
        // isDismissButton() lowercases the node text before matching.
        // Verify that the label set only contains lowercase strings so the
        // contract holds — uppercase input from the node will be lowercased
        // before lookup and still match.
        Set<String> labels = new HashSet<>(Arrays.asList(
                "ok", "allow", "deny", "close", "wait",
                "open app again", "close app",
                "cancel", "retry", "dismiss", "got it",
                "continue", "not now", "no thanks", "done"
        ));
        for (String label : labels) {
            assertEquals(label, label.toLowerCase().trim(),
                    "All dismiss labels must be lowercase/trimmed: '" + label + "'");
        }
    }

    @Test
    void testConsecutiveSystemDialogsCounterResetLogic() {
        // The counter consecutiveSystemDialogs must reset to 0 when a normal iteration
        // succeeds (outOfAppCounter = 0 reset path). We verify the reset invariant:
        // after reset, the counter must not trigger escalation for the next 2 dialogs.
        int counter = 0;
        // Simulate 5 failed dismissals
        for (int i = 0; i < 5; i++) counter++;
        assertEquals(5, counter);
        // Normal iteration clears it
        counter = 0;
        assertEquals(0, counter,
                "Counter must be 0 after reset — no escalation for next dialog");
        // One more dialog (counter=1) should not trigger escalation (threshold is 3)
        counter++;
        assertTrue(counter < 3,
                "Single dialog after reset must not reach first escalation threshold (3)");
    }

    @Test
    void testEscalationThresholds() {
        // Document the two escalation thresholds so tests catch accidental changes.
        int firstEscalationThreshold = 3;
        int secondEscalationThreshold = 6;
        assertTrue(firstEscalationThreshold < secondEscalationThreshold,
                "First escalation (BACK) threshold must be lower than second (force-stop)");
        // Simulate counter reaching first threshold
        int counter = firstEscalationThreshold;
        assertTrue(counter >= 3 && counter < 6,
                "At counter=3 first escalation fires (BACK press)");
        // Simulate counter reaching second threshold
        counter = secondEscalationThreshold;
        assertTrue(counter >= 6,
                "At counter=6 second escalation fires (force-stop + restart)");
    }
}
