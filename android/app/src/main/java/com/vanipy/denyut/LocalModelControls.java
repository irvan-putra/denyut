package com.vanipy.denyut;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Handler;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.chaquo.python.Python;
import org.json.JSONArray;

/** Owner-only UI. No chat command, exported load intent or download client. */
public final class LocalModelControls {
    public static final int PICK_MODEL = 5901;
    private final Activity activity;
    private final Handler handler = new Handler();
    private final TextView status;
    private final Button choose, load, unload, cancel;
    private final Button owner, revoke;
    private boolean attached;
    private final Runnable tick = new Runnable() {
        public void run() {
            status.setText("Local Gemma trial: " + LocalModelWork.status());
            boolean busy = LocalModelWork.busy();
            choose.setEnabled(!busy && "unloaded".equals(LocalGemma.status()));
            load.setEnabled(LocalModelWork.activationAllowed() && !busy && LocalModelWork.imported(activity) && "unloaded".equals(LocalGemma.status()));
            unload.setEnabled(LocalModelWork.activationAllowed() && !busy && !"unloaded".equals(LocalGemma.status()));
            cancel.setEnabled(LocalModelWork.importing());
            if (attached) handler.postDelayed(this, 500);
        }
    };

    public LocalModelControls(Activity activity, LinearLayout layout) {
        this.activity = activity;
        TextView heading = new TextView(activity);
        heading.setText("Optional local Gemma (experimental)\nNo cloud fallback. Model file is separate from APK. No automatic download/load. Load remains disabled pending owner-only routing and asynchronous dispatch review.");
        layout.addView(heading);
        status = new TextView(activity);
        layout.addView(status);
        owner = button(layout, "Select existing verified owner contact");
        revoke = button(layout, "Revoke model owner access");
        owner.setOnClickListener(v -> showOwnerChoices());
        revoke.setOnClickListener(v -> new Thread(() -> {
            try { Python.getInstance().getModule("android_bot").callAttr("revoke_local_owner"); }
            catch (Exception ignored) { }
        }, "denyut-owner-revoke").start());
        choose = button(layout, "Choose downloaded model file");
        load = button(layout, "Load local model");
        unload = button(layout, "Unload local model");
        cancel = button(layout, "Cancel file import");
        choose.setOnClickListener(v -> new AlertDialog.Builder(activity)
                .setTitle("Import 2.59 GB model file?")
                .setMessage("Choose the generic gemma-4-E2B-it.litertlm file you downloaded separately. This app will not download it. Import copies 2.59 GB into private app storage and checks its SHA-256. Keep at least that much extra space plus headroom. No file is sent to a cloud model. Model remains unloaded until you tap Load.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Choose file", (dialog, which) -> {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    activity.startActivityForResult(intent, PICK_MODEL);
                }).show());
        load.setOnClickListener(v -> new AlertDialog.Builder(activity)
                .setTitle("Activate local model?")
                .setMessage("CPU text-only trial. Loading may be slow or fail on this device and cannot be cancelled safely yet. Free-form bot replies use this model while loaded. Commands stay separate. No remote fallback. The model will not reload after process restart.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Load", (dialog, which) -> LocalModelWork.load(activity)).show());
        unload.setOnClickListener(v -> LocalModelWork.unload());
        cancel.setOnClickListener(v -> LocalModelWork.cancelImport());
    }
    private void showOwnerChoices() {
        owner.setEnabled(false);
        new Thread(() -> {
            try {
                JSONArray choices = new JSONArray(Python.getInstance().getModule("android_bot")
                        .callAttr("local_owner_choices").toString());
                String[] labels = new String[choices.length()];
                for (int i = 0; i < labels.length; i++) labels[i] = choices.getJSONObject(i).getString("label");
                activity.runOnUiThread(() -> {
                    if (!attached || activity.isFinishing()) return;
                    owner.setEnabled(true);
                    if (labels.length == 0) {
                        new AlertDialog.Builder(activity).setTitle("No eligible owner contact")
                                .setMessage("Start the bot with an already-paired verified encrypted one-to-one contact. This picker never creates accounts or pairs contacts.")
                                .setPositiveButton("OK", null).show();
                        return;
                    }
                    new AlertDialog.Builder(activity).setTitle("Choose existing verified peer")
                            .setItems(labels, (dialog, which) -> new AlertDialog.Builder(activity)
                                    .setTitle("Allow this contact to use local model?")
                                    .setMessage(labels[which] + "\nSession only. Confirm both account and peer address. Names alone are not identity. Once activated, this contact can use this phone CPU and battery for free-form replies. Only the first 200 existing chats per account are listed. Activation remains disabled pending runtime and UI verification.")
                                    .setNegativeButton("Cancel", null)
                                    .setPositiveButton("Confirm owner", (confirm, selected) -> new Thread(() -> {
                                        boolean ok = false;
                                        try { ok = Python.getInstance().getModule("android_bot")
                                                .callAttr("select_local_owner", choices.getJSONObject(which).getString("token")).toBoolean(); }
                                        catch (Exception ignored) { }
                                        final boolean success = ok;
                                        activity.runOnUiThread(() -> {
                                            if (!attached || activity.isFinishing()) return;
                                            new AlertDialog.Builder(activity).setMessage(success ? "Session owner selected. Free-form replies will say the local model is unloaded until activation is available. No cloud fallback. Commands still work." : "Choice expired or verification changed. Refresh picker.")
                                                    .setPositiveButton("OK", null).show();
                                        });
                                    }, "denyut-owner-select").start()).show())
                            .setNegativeButton("Cancel", null).show();
                });
            } catch (Exception failure) {
                activity.runOnUiThread(() -> {
                    if (attached && !activity.isFinishing()) {
                        owner.setEnabled(true);
                        new AlertDialog.Builder(activity).setMessage("Owner choices unavailable. Start the bot and try again.")
                                .setPositiveButton("OK", null).show();
                    }
                });
            }
        }, "denyut-owner-choices").start();
    }

    private Button button(LinearLayout layout, String text) {
        Button button = new Button(activity);
        button.setText(text);
        layout.addView(button);
        return button;
    }
    public void attach() { attached = true; owner.setEnabled(true); handler.post(tick); }
    public void detach() { attached = false; handler.removeCallbacks(tick); }
}
