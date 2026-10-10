package androidx.compose.ui.semantics;

public final class AccessibilityAction {
    private final Object action;

    public AccessibilityAction(Object action) {
        this.action = action;
    }

    public Object getAction() {
        return action;
    }
}
