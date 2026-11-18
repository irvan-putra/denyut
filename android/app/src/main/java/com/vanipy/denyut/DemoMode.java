package com.vanipy.denyut;

import android.content.Context;

/** Opt-in switch that makes the widget show the bundled made-up data instead of the real store. */
public final class DemoMode {
    private static final String PREFS = "denyut_prefs";
    private static final String KEY = "demo_mode";

    private DemoMode() {}

    public static boolean isOn(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY, false);
    }

    public static void set(Context c, boolean on) {
        c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY, on).apply();
        DenyutWidgetProvider.updateAll(c);
    }
}
