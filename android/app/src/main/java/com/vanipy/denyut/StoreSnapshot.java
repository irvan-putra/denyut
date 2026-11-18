package com.vanipy.denyut;

import android.content.Context;
import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Read-only view of the bot's on-device store (files/store/notes.json and
 * files/store/reminders.json), so the widget can show the next pending
 * reminder and the open-notes count without starting Python.
 */
public final class StoreSnapshot {
    public final int openNotes;
    public final String nextReminderText;   // null when nothing is pending
    public final long nextReminderDueMs;

    private StoreSnapshot(int openNotes, String nextReminderText, long nextReminderDueMs) {
        this.openNotes = openNotes;
        this.nextReminderText = nextReminderText;
        this.nextReminderDueMs = nextReminderDueMs;
    }

    public static StoreSnapshot read(Context c) {
        File store = new File(c.getFilesDir(), "store");
        int notes = 0;
        JSONObject notesJson = readJson(new File(store, "notes.json"));
        if (notesJson != null) {
            for (Iterator<String> it = notesJson.keys(); it.hasNext(); ) {
                JSONObject per = notesJson.optJSONObject(it.next());
                JSONArray open = per == null ? null : per.optJSONArray("open");
                if (open != null) notes += open.length();
            }
        }
        String text = null;
        long due = Long.MAX_VALUE;
        JSONObject remindersJson = readJson(new File(store, "reminders.json"));
        if (remindersJson != null) {
            for (Iterator<String> it = remindersJson.keys(); it.hasNext(); ) {
                JSONObject per = remindersJson.optJSONObject(it.next());
                JSONArray pending = per == null ? null : per.optJSONArray("pending");
                if (pending == null) continue;
                for (int i = 0; i < pending.length(); i++) {
                    JSONObject r = pending.optJSONObject(i);
                    if (r == null) continue;
                    long d = r.optLong("due", Long.MAX_VALUE);
                    if (d == Long.MAX_VALUE) continue;
                    // The bot stores time.time() epoch seconds; the widget works in ms.
                    if (d < 1_000_000_000_000L) d *= 1000L;
                    if (d < due) { due = d; text = r.optString("text", null); }
                }
            }
        }
        return new StoreSnapshot(notes, text, due);
    }

    private static JSONObject readJson(File f) {
        if (!f.exists()) return null;
        try (FileInputStream in = new FileInputStream(f)) {
            byte[] buf = new byte[(int) f.length()];
            int off = 0, n;
            while (off < buf.length && (n = in.read(buf, off, buf.length - off)) > 0) off += n;
            return new JSONObject(new String(buf, 0, off, StandardCharsets.UTF_8));
        } catch (Exception e) {
            return null;
        }
    }
}
