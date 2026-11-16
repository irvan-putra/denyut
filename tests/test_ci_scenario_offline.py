"""Offline qualification of the notes + reminders CI scenario.

No network, no deltachat2, no accounts. The scenario logic in
tools/ci_chat_scenario.py is driven against the REAL Assistant (the same
core the Android bot calls) with a fake clock and a fake 30s reminder
timer, plus deliberately broken bots that the scenario must reject.

What this proves: the assertions are right for the real command formats,
and they fail when notes do not archive, a reminder never fires, or a
reminder fires before its delay. What it does not prove: anything about
Android, DeltaChat delivery, relay latency or the real timer thread. Only
the emulator run covers those.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import ci_chat_scenario as sc  # noqa: E402
from denyut.core import Assistant  # noqa: E402

BEHAVIOR = os.path.join(REPO_ROOT, "android", "app", "src", "main", "python",
                        "behavior.json")
POLL = 30  # the adapter's REMINDER_POLL_SECONDS


class Harness:
    """Fake chat: commands go to the real Assistant, replies queue up,
    and the reminder timer ticks every POLL seconds of fake time while
    the scenario is waiting."""

    def __init__(self, store_dir, fire_early=False, never_fire=False,
                 pre_notes=0, slow_ack_jump=0):
        self.now = 1_000_000.0
        self.a = Assistant(behavior_path=BEHAVIOR, store_dir=str(store_dir))
        self.queue = []
        self.sent = []
        self.fire_early = fire_early
        self.slow_ack_jump = slow_ack_jump
        self.never_fire = never_fire
        self.log = []
        for i in range(pre_notes):
            self.a.handle("/note older note %d" % i, sender="42", now=self.now)

    def clock(self):
        return self.now

    def send(self, text):
        self.sent.append(text)
        if self.slow_ack_jump and text == "/reminders":
            # the relay is slow: the bot's timer fires before our ack lands
            self.now += self.slow_ack_jump
            self.tick()
        self.queue.append(self.a.handle(text, sender="42", now=self.now))
        if self.fire_early and text == "/reminders":  # fires right after the pending check
            for _s, t in self.a.due_reminders(now=self.now + 10_000):
                self.queue.append("Reminder: " + t)

    def tick(self):
        if self.never_fire:
            return
        for _s, t in self.a.due_reminders(now=self.now):
            self.queue.append("Reminder: " + t)

    def wait(self, pred, timeout_s):
        waited = 0
        while True:
            while self.queue:
                t = self.queue.pop(0)
                if pred(t):
                    return t
            if waited >= timeout_s:
                return None
            self.now += POLL
            waited += POLL
            self.tick()

    def run(self):
        return sc.run(self.send, self.wait, sc.new_marker(), self.clock,
                      self.log.append)


def test_scenario_passes_against_real_assistant(tmp_path):
    h = Harness(tmp_path)
    ok, step = h.run()
    assert ok, (step, h.log)
    assert h.sent[-1] == "/reminders", "no command may follow the reminder check"


def test_note_number_is_read_not_assumed(tmp_path):
    h = Harness(tmp_path, pre_notes=3)
    ok, step = h.run()
    assert ok, (step, h.log)
    assert any(s == "/done 4" for s in h.sent), h.sent
    assert "older note 0" in "\n".join(
        h.a.handle("/notes", sender="42", now=h.now).splitlines()), \
        "scenario must only archive its own marker"


def test_fails_when_reminder_never_fires(tmp_path):
    ok, step = Harness(tmp_path, never_fire=True).run()
    assert (ok, step) == (False, "reminder-unsolicited")


def test_fails_when_reminder_fires_before_delay(tmp_path):
    ok, step = Harness(tmp_path, fire_early=True).run()
    assert (ok, step) == (False, "reminder-unsolicited")


def test_fails_when_done_does_not_archive(tmp_path):
    h = Harness(tmp_path)
    real = h.a.handle

    def broken(text, sender="local", now=None):
        if text.startswith("/done"):
            return "Done: stub (kept in archive)"  # lies, archives nothing
        return real(text, sender=sender, now=now)

    h.a.handle = broken
    ok, step = h.run()
    assert not ok and step in ("note-archive", "note-gone-from-list"), step


def test_fails_when_notes_silent(tmp_path):
    h = Harness(tmp_path)
    h.a.handle = lambda text, sender="local", now=None: "ok"
    ok, step = h.run()
    assert (ok, step) == (False, "note-create")


def test_log_carries_only_step_lines(tmp_path):
    h = Harness(tmp_path)
    h.run()
    for line in h.log:
        assert line.startswith("scenario "), line
        assert "dnt-" not in line and "@" not in line


def test_reminder_arriving_before_pending_ack_is_kept(tmp_path):
    """Review finding: a correctly timed reminder that lands while the
    scenario waits for the /reminders reply must not be discarded."""
    h = Harness(tmp_path, slow_ack_jump=61)
    ok, step = h.run()
    assert ok, (step, h.log)
    assert h.sent[-1] == "/reminders"


def test_early_reminder_during_pending_ack_is_still_rejected(tmp_path):
    """Same overlap, but the reminder is too early: must still fail."""
    h = Harness(tmp_path, slow_ack_jump=20)
    orig = h.a.handle

    def short(text, sender="local", now=None):
        if text.startswith("/remind "):
            text = text.replace("60s", "10s")
        return orig(text, sender=sender, now=now)

    h.a.handle = short
    ok, step = h.run()
    assert not ok and step == "reminder-unsolicited", (ok, step, h.log)
