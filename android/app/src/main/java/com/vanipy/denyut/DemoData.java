package com.vanipy.denyut;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

/**
 * Made-up notes and a made-up meetup reminder for showing denyut to friends.
 * Every entry is invented sample content bundled with the app, not the owner's
 * real notes. Demo mode is opt-in and labeled DEMO on the widget.
 */
public final class DemoData {
    private DemoData() {}

    public static List<String> notes() {
        List<String> n = new ArrayList<>();
        n.add("Ideas for the weekend photo walk");
        n.add("Ask Rani about the workshop slot");
        n.add("Book club pick: short stories");
        n.add("Back up the travel photos");
        n.add("Try the new noodle place");
        n.add("Call the bike shop about the brakes");
        return n;
    }

    public static String reminderText() {
        return "Leave for the meetup";
    }

    /** Due time for the demo reminder: the next 17:30, today or tomorrow. */
    public static long reminderDueMs(long nowMs) {
        Calendar cal = Calendar.getInstance();
        cal.set(Calendar.HOUR_OF_DAY, 17); cal.set(Calendar.MINUTE, 30);
        cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0);
        if (cal.getTimeInMillis() <= nowMs) cal.add(Calendar.DAY_OF_YEAR, 1);
        return cal.getTimeInMillis();
    }
}
