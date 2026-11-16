"""Notes + reminders scenario for the Denyut CI chat witness.

Pure logic, no deltachat2 import: the caller supplies how to send a
message to the bot and how to wait for the bot's next matching reply.
That keeps the assertions testable offline against the real Assistant.

Steps (each command waits for its own reply before the next is sent):
  1. /note <marker>        -> reply "Noted (<n>): <marker>"
  2. /notes                -> a numbered line containing the marker
  3. /done <n>             -> "Done: <marker> (kept in archive)"
                              n is read from step 2, never assumed
  4. /notes                -> a notes-shaped reply WITHOUT the marker
  5. /remind <delay> <marker> -> "Okay, reminding you in ...: <marker>"
  6. /reminders            -> a line containing the marker
  7. send NOTHING, wait    -> "Reminder: <marker>" arrives on its own,
                              not before about DELAY seconds

A matching "Reminder: <marker>" seen during ANY earlier wait (a slow ack
can let the timer fire first) is remembered with the time it was seen,
not discarded, and judged at step 7 by the same timing rule. Commands
never fire reminders in the adapter, so a reminder that is late enough
is timer-driven even if it overlaps the last ack. Only that one message
is buffered; everything else unmatched is still ignored.

Only the synthetic marker is ever matched or printed. Bot text is never
echoed to the log, because the public CI log must stay free of
identifiers.
"""

import re
import uuid

REMIND_DELAY_S = 60
NOTE_REPLY_TIMEOUT_S = 120
REMINDER_WAIT_S = 240
EARLY_SLACK_S = 5


def new_marker():
    return "dnt-" + uuid.uuid4().hex[:12]


def _numbered_line(text, marker):
    for line in (text or "").splitlines():
        m = re.fullmatch(r"(\d+)\. (.*)", line.strip())
        if m and marker in m.group(2):
            return int(m.group(1))
    return None


def _is_notes_reply(text):
    t = (text or "").strip()
    return t.startswith("No notes yet") or re.match(r"\d+\. ", t) is not None


def run(send, wait, marker, clock, log):
    """Return (True, "") or (False, "<step name>").

    send(text)            sends one command to the bot
    wait(pred, timeout_s) returns the first incoming text for which
                          pred(text) is true, or None on timeout
    clock()               seconds, monotonic enough for the delay check
    log(line)             prints a public-safe progress line
    """
    seen = []  # clock() when a matching reminder was first seen

    def wait_keep(pred, timeout_s):
        def p(t):
            if t.startswith("Reminder: ") and marker in t and not seen:
                seen.append(clock())
            return pred(t)
        return wait(p, timeout_s)

    def step(name, ok):
        log("scenario %s: %s" % (name, "ok" if ok else "FAIL"))
        return (True, "") if ok else (False, name)

    send("/note " + marker)
    r = wait_keep(lambda t: t.startswith("Noted (") and marker in t, NOTE_REPLY_TIMEOUT_S)
    if r is None:
        return step("note-create", False)
    step("note-create", True)

    send("/notes")
    r = wait_keep(lambda t: _numbered_line(t, marker) is not None, NOTE_REPLY_TIMEOUT_S)
    if r is None:
        return step("note-list", False)
    n = _numbered_line(r, marker)
    step("note-list", True)

    send("/done %d" % n)
    r = wait_keep(lambda t: t.startswith("Done: ") and marker in t
             and "kept in archive" in t, NOTE_REPLY_TIMEOUT_S)
    if r is None:
        return step("note-archive", False)
    step("note-archive", True)

    send("/notes")
    r = wait_keep(_is_notes_reply, NOTE_REPLY_TIMEOUT_S)
    if r is None:
        return step("note-gone-from-list", False)
    if marker in r:
        return step("note-gone-from-list", False)
    step("note-gone-from-list", True)

    t_send = clock()
    send("/remind %ds %s" % (REMIND_DELAY_S, marker))
    r = wait_keep(lambda t: t.startswith("Okay, reminding you in") and marker in t,
             NOTE_REPLY_TIMEOUT_S)
    if r is None:
        return step("reminder-create", False)
    step("reminder-create", True)

    send("/reminders")
    # If the timer already fired (slow ack), the list is empty by then.
    r = wait_keep(lambda t: (marker in t and "(in " in t)
                  or (seen and t.startswith("No pending reminders")),
                  NOTE_REPLY_TIMEOUT_S)
    if r is None:
        return step("reminder-pending", False)
    step("reminder-pending", True)

    # No command from here on: the next message must come from the bot's
    # own timer. Anything that is not the reminder is ignored by wait().
    if seen:
        got = seen[0]
    else:
        r = wait_keep(lambda t: t.startswith("Reminder: ") and marker in t,
                      REMINDER_WAIT_S)
        if r is None:
            return step("reminder-unsolicited", False)
        got = seen[0]
    elapsed = got - t_send
    if elapsed < REMIND_DELAY_S - EARLY_SLACK_S:
        log("scenario reminder-unsolicited: arrived after %ds, before the delay"
            % int(elapsed))
        return step("reminder-unsolicited", False)
    log("scenario reminder-unsolicited: arrived after about %ds" % int(elapsed))
    return step("reminder-unsolicited", True)
