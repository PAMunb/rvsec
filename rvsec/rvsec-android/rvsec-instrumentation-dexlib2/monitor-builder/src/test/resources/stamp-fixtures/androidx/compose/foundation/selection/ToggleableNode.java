package androidx.compose.foundation.selection;

import androidx.compose.foundation.ClickableNode;
import kotlin.jvm.functions.Function1;

/** Its onClick is the library's own wrapper; the app's callback is onValueChange. */
public class ToggleableNode extends ClickableNode {
    public boolean value;
    public Function1 onValueChange;
}
