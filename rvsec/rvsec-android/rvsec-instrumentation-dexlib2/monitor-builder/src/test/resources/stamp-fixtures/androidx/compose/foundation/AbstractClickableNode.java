package androidx.compose.foundation;

import kotlin.jvm.functions.Function0;

/** Base of the foundation 1.9 clickable modifier nodes; holds the app's click lambda. */
public abstract class AbstractClickableNode {
    public boolean enabled = true;
    public Function0 onClick;
}
