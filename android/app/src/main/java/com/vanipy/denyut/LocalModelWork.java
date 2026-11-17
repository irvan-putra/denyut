package com.vanipy.denyut;

import android.content.Context;
import android.net.Uri;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Process-scoped work, no Activity reference. No automatic reload after death.
 * Activity may disappear/recreate without leaking views or canceling unexpectedly.
 * Import cancellation is cooperative between stream reads; blocked provider reads
 * are not guaranteed interruptible. Native loading is not cancellable here.
 */
public final class LocalModelWork {
    private static final ExecutorService WORKER = Executors.newSingleThreadExecutor();
    private static final AtomicBoolean CANCEL = new AtomicBoolean();
    private static volatile boolean busy;
    private static volatile boolean importing;
    private static volatile String detail = "No model imported or loaded automatically.";
    private LocalModelWork() {}
    public static boolean activationAllowed() { return false; } // safety gate until owner/dispatch reviewed
    public static boolean busy() { return busy; }
    public static boolean importing() { return importing; }
    public static String status() { return LocalGemma.status() + ": " + detail; }
    private static File model(Context c) { return new File(c.getFilesDir(), "local-model/gemma4-e2b.litertlm"); }
    public static boolean imported(Context c) { return model(c).isFile(); }

    public static synchronized void importSelected(Context context, Uri uri) {
        if (busy || !"unloaded".equals(LocalGemma.status())) return;
        Context app = context.getApplicationContext();
        busy = true;
        importing = true;
        CANCEL.set(false);
        detail = "Importing selected file...";
        WORKER.execute(() -> {
            try {
                File target = model(app);
                File parent = target.getParentFile();
                if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException();
                // Remove only this component's abandoned partial imports, never vault data.
                File[] stale = parent.listFiles((dir, name) -> name.startsWith("model-import-") && name.endsWith(".part"));
                if (stale != null) for (File file : stale) file.delete();
                // Space for a complete NEW file; existing model isn't deleted first.
                // Headroom is preflight only; other processes can consume storage.
                long headroom = 256L * 1024 * 1024;
                if (parent.getUsableSpace() < ModelFile.EXPECTED_BYTES + headroom) {
                    detail = "Not enough free space for import plus 256 MiB headroom.";
                    return;
                }
                try (InputStream in = app.getContentResolver().openInputStream(uri)) {
                    if (in == null) throw new IOException();
                    ModelFile.importSelected(in, target, bytes -> {
                        if (CANCEL.get()) throw new IOException("Cancelled");
                        detail = "Import " + (bytes * 100 / ModelFile.EXPECTED_BYTES) + "% (hash checked before install)";
                    });
                }
                detail = "Imported and verified. Tap Load to activate locally.";
            } catch (Exception failure) {
                detail = CANCEL.get() ? "Import cancelled; previous file kept." : "Import failed; previous file kept. Check file and space.";
            } finally { importing = false; busy = false; }
        });
    }

    public static void cancelImport() { if (importing) CANCEL.set(true); }

    public static synchronized void load(Context context) {
        if (!activationAllowed()) { detail = "Activation gated: owner-only sender binding and asynchronous dispatch still need verification."; return; }
        if (busy || !"unloaded".equals(LocalGemma.status())) return;
        Context app = context.getApplicationContext();
        busy = true;
        detail = "Verifying/loading on CPU. Native load cannot be cancelled safely here.";
        WORKER.execute(() -> {
            try {
                LocalGemma.load(model(app).getAbsolutePath(), new File(app.getCacheDir(), "gemma").getAbsolutePath());
                detail = "Local text model active for bot free-form replies; no cloud fallback.";
            } catch (Exception failure) { detail = "Load failed. Commands still work. No cloud request made."; }
            finally { busy = false; }
        });
    }

    public static synchronized void unload() {
        if (busy) return;
        busy = true;
        WORKER.execute(() -> {
            try { LocalGemma.unload(); detail = "Unloaded. Imported file remains on disk."; }
            catch (Exception failure) { detail = "Model is busy; wait for generation and try Unload again."; }
            finally { busy = false; }
        });
    }
}
