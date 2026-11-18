package com.vanipy.denyut;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.text.format.DateFormat;
import android.view.View;
import android.os.Bundle;
import android.widget.RemoteViews;
import java.util.Date;
import java.util.List;

/** Home-screen widget: the next pending reminder and the open-notes count. Tap opens denyut. */
public class DenyutWidgetProvider extends AppWidgetProvider {

    @Override
    public void onUpdate(Context context, AppWidgetManager mgr, int[] appWidgetIds) {
        for (int id : appWidgetIds) mgr.updateAppWidget(id, buildViews(context, mgr.getAppWidgetOptions(id)));
    }

    public static void updateAll(Context context) {
        AppWidgetManager mgr = AppWidgetManager.getInstance(context);
        int[] ids = mgr.getAppWidgetIds(new ComponentName(context, DenyutWidgetProvider.class));
        for (int id : ids) mgr.updateAppWidget(id, buildViews(context, mgr.getAppWidgetOptions(id)));
    }

    @Override
    public void onAppWidgetOptionsChanged(Context c, AppWidgetManager mgr, int id, Bundle options) {
        mgr.updateAppWidget(id, buildViews(c, options));
    }

    static RemoteViews buildViews(Context c, Bundle options) {
        int height = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT, 48);
        return buildViews(c, height < 110, options.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 48) < 100);
    }

    static RemoteViews buildViews(Context c) { return buildViews(c, false); }

    static RemoteViews buildViews(Context c, boolean compact) { return buildViews(c, compact, false); }

    static RemoteViews buildViews(Context c, boolean compact, boolean tiny) {
        RemoteViews v = new RemoteViews(c.getPackageName(), tiny ? R.layout.widget_denyut_tiny : compact ? R.layout.widget_denyut_compact : R.layout.widget_denyut);
        boolean demo = DemoMode.isOn(c);
        v.setViewVisibility(R.id.widget_demo_badge, View.GONE);

        String reminderText;
        long dueMs;
        int notes;
        if (demo) {
            List<String> demoNotes = DemoData.notes();
            notes = demoNotes.size();
            reminderText = DemoData.reminderText();
            dueMs = DemoData.reminderDueMs(System.currentTimeMillis());
        } else {
            StoreSnapshot snap = StoreSnapshot.read(c);
            notes = snap.openNotes;
            reminderText = snap.nextReminderText;
            dueMs = snap.nextReminderDueMs;
        }

        if (reminderText == null) {
            v.setTextViewText(R.id.widget_reminder, "No pending reminders");
            v.setTextViewText(R.id.widget_reminder_due, "Ask denyut for one with /remind");
        } else {
            v.setTextViewText(R.id.widget_reminder, reminderText);
            v.setTextViewText(R.id.widget_reminder_due, formatDue(dueMs));
        }
        String noteText = notes == 1 ? "1 note open" : notes + " notes open";
        v.setTextViewText(R.id.widget_notes, noteText);
        if (compact) {
            String due = reminderText == null ? "Ask denyut with /remind" : formatDue(dueMs);
            v.setTextViewText(R.id.widget_reminder_due, due + " · " + noteText);
        }

        if (tiny) {
            v.setContentDescription(R.id.widget_root, "denyut: " + (reminderText == null ? "No pending reminder" : reminderText + ", " + formatDue(dueMs)) + ". " + noteText);
            v.setTextViewText(R.id.widget_reminder, notes > 999 ? "999+" : String.valueOf(notes));
            v.setTextViewText(R.id.widget_reminder_due, "notes");
        }

        PendingIntent pi = PendingIntent.getActivity(c, 0,
                new Intent(c, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
        v.setOnClickPendingIntent(R.id.widget_root, pi);
        return v;
    }

    private static String formatDue(long dueMs) {
        return formatDue(dueMs, System.currentTimeMillis());
    }

    /** All times are epoch millis; countdown is absolute and the clock time renders in the device default timezone. */
    static String formatDue(long dueMs, long nowMs) {
        long left = dueMs - nowMs;
        if (left <= 0) return "due now";
        long days = left / 86_400_000L;
        Date d = new Date(dueMs);
        if (days >= 1) return DateFormat.format("EEE d MMM, HH:mm", d).toString();
        long h = left / 3_600_000L;
        long m = (left % 3_600_000L) / 60_000L;
        if (h > 0) return "in " + h + " h " + m + " min (" + DateFormat.format("HH:mm", d) + ")";
        return "in " + Math.max(m, 1) + " min (" + DateFormat.format("HH:mm", d) + ")";
    }
}
