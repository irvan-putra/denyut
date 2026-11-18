package com.vanipy.denyut;

import static org.junit.Assert.*;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

/**
 * The widget shows a countdown and a clock time for the next reminder.
 * Both must agree in the owner's timezone (Asia/Jakarta): the countdown is
 * absolute epoch math and the wall-clock time must render in the device
 * default timezone, never UTC. These tests pin the default zone to Jakarta
 * and cover the 17:30 demo due rolling over to the next day.
 */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34)
public class WidgetDueFormatTest {
    private TimeZone saved;

    @Before
    public void pinJakarta() {
        saved = TimeZone.getDefault();
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Jakarta"));
    }

    @After
    public void restoreZone() {
        TimeZone.setDefault(saved);
    }

    /** Wall-clock time in the pinned zone, for building fixed instants. */
    private static long at(int year, int month, int day, int hour, int minute) {
        Calendar c = Calendar.getInstance();
        c.clear();
        c.set(year, month, day, hour, minute);
        return c.getTimeMillis();
    }

    private static String jakartaClock(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("HH:mm", Locale.US);
        f.setTimeZone(TimeZone.getTimeZone("Asia/Jakarta"));
        return f.format(new Date(ms));
    }

    @Test
    public void demoDueIsNextHalfPastFiveInLocalTime() {
        // 04:00 in Jakarta -> today 17:30 Jakarta.
        long morning = at(2026, Calendar.NOVEMBER, 18, 4, 0);
        long due = DemoData.reminderDueMs(morning);
        assertEquals(at(2026, Calendar.NOVEMBER, 18, 17, 30), due);
        assertEquals("17:30", jakartaClock(due));
    }

    @Test
    public void demoDueRollsToTomorrowAfterHalfPastFive() {
        long evening = at(2026, Calendar.NOVEMBER, 18, 18, 0);
        long due = DemoData.reminderDueMs(evening);
        assertEquals(at(2026, Calendar.NOVEMBER, 19, 17, 30), due);
    }

    @Test
    public void demoDueRollsAtExactlyHalfPastFive() {
        long exactly = at(2026, Calendar.NOVEMBER, 18, 17, 30);
        long due = DemoData.reminderDueMs(exactly);
        assertEquals(at(2026, Calendar.NOVEMBER, 19, 17, 30), due);
    }

    @Test
    public void countdownAndClockAgreeAcrossMidnight() {
        // 23:30 Jakarta, due 17:30 next day: 18 h away, clock shows 17:30.
        long now = at(2026, Calendar.NOVEMBER, 18, 23, 30);
        long due = at(2026, Calendar.NOVEMBER, 19, 17, 30);
        assertEquals("in 18 h 0 min (17:30)", DenyutWidgetProvider.formatDue(due, now));
    }

    @Test
    public void countdownRendersClockInLocalZoneNotUtc() {
        // 04:00 Jakarta, due 17:30: 13 h 30 min; the bracketed time must be
        // the Jakarta wall clock (17:30), not the UTC one (10:30).
        long now = at(2026, Calendar.NOVEMBER, 18, 4, 0);
        long due = at(2026, Calendar.NOVEMBER, 18, 17, 30);
        assertEquals("in 13 h 30 min (17:30)", DenyutWidgetProvider.formatDue(due, now));
    }

    @Test
    public void underAnHourShowsMinutes() {
        long now = at(2026, Calendar.NOVEMBER, 18, 9, 0);
        long due = now + 12 * 60_000L;
        assertEquals("in 12 min (09:12)", DenyutWidgetProvider.formatDue(due, now));
    }

    @Test
    public void pastDueShowsDueNow() {
        long now = at(2026, Calendar.NOVEMBER, 18, 9, 0);
        assertEquals("due now", DenyutWidgetProvider.formatDue(now - 60_000L, now));
        assertEquals("due now", DenyutWidgetProvider.formatDue(now, now));
    }

    @Test
    public void beyondADayShowsDateInLocalZone() {
        long now = at(2026, Calendar.NOVEMBER, 18, 9, 0);
        long due = now + 49L * 3_600_000L; // Thu -> Sat 10:00 Jakarta
        String expected = new SimpleDateFormat("EEE d MMM, HH:mm", Locale.US).format(new Date(due));
        // The expected string is computed with the pinned default zone, so a
        // UTC render inside the widget would differ and fail this test.
        assertEquals(expected, DenyutWidgetProvider.formatDue(due, now));
        assertTrue(expected.contains("10:00"));
    }
}
