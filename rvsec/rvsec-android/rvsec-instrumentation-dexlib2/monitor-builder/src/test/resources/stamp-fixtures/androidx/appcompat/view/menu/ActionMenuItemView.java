package androidx.appcompat.view.menu;

import android.content.Context;
import android.view.View;

/** A menu item view; the tests allocate it without running a constructor. */
public class ActionMenuItemView extends View {
    private MenuItemImpl mItemData;

    public ActionMenuItemView(Context context) {
        super(context);
    }

    public MenuItemImpl getItemData() {
        return mItemData;
    }
}
