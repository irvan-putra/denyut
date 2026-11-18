package com.vanipy.denyut;

import static org.junit.Assert.*;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.RemoteViews;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileWriter;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

/** Resource rendering checks only. Real host qualification is separate. */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class WidgetRenderTest {
    private int W = 660, H = 320;

    private void snapshot(RemoteViews rv, Context c, String outName) throws Exception {
        FrameLayout parent = new FrameLayout(c);
        View v = rv.apply(c, parent);
        v.measure(View.MeasureSpec.makeMeasureSpec(W, View.MeasureSpec.EXACTLY),
                  View.MeasureSpec.makeMeasureSpec(H, View.MeasureSpec.EXACTLY));
        v.layout(0, 0, W, v.getMeasuredHeight());
        Bitmap bmp = Bitmap.createBitmap(W, v.getMeasuredHeight(), Bitmap.Config.ARGB_8888);
        v.draw(new Canvas(bmp));
        File out = new File("build/widget-snapshots", outName);
        out.getParentFile().mkdirs();
        try (FileOutputStream fos = new FileOutputStream(out)) {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, fos);
        }
        assertTrue(out.length() > 300);
    }

    @Test
    @Config(qualifiers = "mdpi")
    public void counterAndCompactResize() throws Exception {
        Context c = RuntimeEnvironment.getApplication();
        DemoMode.set(c, true);
        android.os.Bundle options = new android.os.Bundle();
        options.putInt(android.appwidget.AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 64);
        options.putInt(android.appwidget.AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 64);
        W = 64; H = 64;
        snapshot(DenyutWidgetProvider.buildViews(c, options), c, "widget-counter-64dp.png");
        options.putInt(android.appwidget.AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 350);
        W = 350;
        snapshot(DenyutWidgetProvider.buildViews(c, options), c, "widget-strip-350x64dp.png");
        options.putInt(android.appwidget.AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 180);
        H = 180;
        snapshot(DenyutWidgetProvider.buildViews(c, options), c, "widget-expanded-350x180dp.png");
        DemoMode.set(c, false);
    }

    @Test
    public void widgetDemoMode() throws Exception {
        Context c = RuntimeEnvironment.getApplication();
        DemoMode.set(c, true);
        snapshot(DenyutWidgetProvider.buildViews(c), c, "widget-demo.png");
        assertTrue(DemoData.reminderDueMs(System.currentTimeMillis()) > System.currentTimeMillis());
        c.getSharedPreferences("denyut_prefs", Context.MODE_PRIVATE).edit().clear().commit();
    }

    @Test
    public void widgetReadsRealStore() throws Exception {
        Context c = RuntimeEnvironment.getApplication();
        File store = new File(c.getFilesDir(), "store");
        store.mkdirs();
        // The bot writes time.time() epoch seconds.
        long dueSec = (System.currentTimeMillis() + 90 * 60_000L) / 1000L;
        JSONObject perSender = new JSONObject()
                .put("pending", new org.json.JSONArray().put(new JSONObject()
                        .put("text", "Water the plants").put("due", dueSec)))
                .put("done", new org.json.JSONArray());
        JSONObject reminders = new JSONObject().put("owner@test", perSender);
        try (FileWriter w = new FileWriter(new File(store, "reminders.json"))) {
            w.write(reminders.toString());
        }
        JSONObject notesPer = new JSONObject()
                .put("open", new org.json.JSONArray().put("first").put("second").put("third"))
                .put("archived", new org.json.JSONArray());
        try (FileWriter w = new FileWriter(new File(store, "notes.json"))) {
            w.write(new JSONObject().put("owner@test", notesPer).toString());
        }
        StoreSnapshot snap = StoreSnapshot.read(c);
        assertEquals(3, snap.openNotes);
        assertEquals("Water the plants", snap.nextReminderText);
        assertTrue(snap.nextReminderDueMs > System.currentTimeMillis());
        snapshot(DenyutWidgetProvider.buildViews(c), c, "widget-real.png");
    }

    @Test
    public void widgetDemoHidesRealStore() throws Exception {
        Context c = RuntimeEnvironment.getApplication();
        // Real store present with real-looking content...
        widgetReadsRealStoreFixture(c);
        // ...but demo mode must show only the made-up data.
        DemoMode.set(c, true);
        FrameLayout parent = new FrameLayout(c);
        View v = DenyutWidgetProvider.buildViews(c).apply(c, parent);
        android.widget.TextView reminder = v.findViewById(R.id.widget_reminder);
        android.widget.TextView badge = v.findViewById(R.id.widget_demo_badge);
        android.widget.TextView notes = v.findViewById(R.id.widget_notes);
        assertEquals(DemoData.reminderText(), reminder.getText().toString());
        assertEquals(View.VISIBLE, badge.getVisibility());
        assertEquals(DemoData.notes().size() + " notes open", notes.getText().toString());
        c.getSharedPreferences("denyut_prefs", Context.MODE_PRIVATE).edit().clear().commit();
        new File(c.getFilesDir(), "store/notes.json").delete();
        new File(c.getFilesDir(), "store/reminders.json").delete();
    }

    private void widgetReadsRealStoreFixture(Context c) throws Exception {
        File store = new File(c.getFilesDir(), "store");
        store.mkdirs();
        JSONObject perSender = new JSONObject()
                .put("pending", new org.json.JSONArray().put(new JSONObject()
                        .put("text", "Real private reminder").put("due", 4_000_000_000L)))
                .put("done", new org.json.JSONArray());
        try (FileWriter w = new FileWriter(new File(store, "reminders.json"))) {
            w.write(new JSONObject().put("owner@test", perSender).toString());
        }
        JSONObject notesPer = new JSONObject()
                .put("open", new org.json.JSONArray().put("real private note"))
                .put("archived", new org.json.JSONArray());
        try (FileWriter w = new FileWriter(new File(store, "notes.json"))) {
            w.write(new JSONObject().put("owner@test", notesPer).toString());
        }
    }

    @Test
    public void widgetEmptyStore() throws Exception {
        Context c = RuntimeEnvironment.getApplication();
        new File(c.getFilesDir(), "store/notes.json").delete();
        new File(c.getFilesDir(), "store/reminders.json").delete();
        snapshot(DenyutWidgetProvider.buildViews(c), c, "widget-empty.png");
    }
}
