"""Optional local-only Android bridge. No network, download or fallback.

Owner UI is not yet wired: load/import are native owner-side APIs only. A chat
message must never load a model or choose a file. The class is resolved lazily,
so command-only Android startup does not initialize a model/native engine.
"""


class LocalAndroidBackend:
    name = "android-local-gemma"

    def __init__(self, resolve=None):
        self._resolve = resolve or self._java_runtime

    @staticmethod
    def _java_runtime():
        from java import jclass
        return jclass("com.vanipy.denyut.LocalGemma")

    def complete(self, system_prompt, history, user_text):
        # Deliberately stateless trial. Don't share native sessions between
        # senders or include stored notes, reminders or any previous sender.
        if len(system_prompt) + len(user_text) > 1500:
            return "That message is too long for the local model trial. Try a shorter message."
        try:
            runtime = self._resolve()
            state = str(runtime.status())
            if state == "unloaded":
                return "Local model is unloaded. Commands still work. No cloud request was made."
            if state != "ready":
                return "Local model is busy. Commands still work. Try again later."
            reply = str(runtime.complete(system_prompt, user_text)).strip()
            if not reply:
                return "Local model returned no text. Try a shorter message."
            return reply
        except Exception:
            # Native exceptions may include private input/file paths. Never
            # log or forward the exception string; never fall back remotely.
            return "Local model is unavailable. Commands still work. No cloud request was made."
