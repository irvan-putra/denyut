package com.vanipy.denyut;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.InputStream;
import java.util.List;

public class MainActivity extends Activity {
    private final Handler handler = new Handler();
    private TextView statusView;
    private LocalModelControls localControls;
    private boolean noticesLoading;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        statusView = new TextView(this);
        Button startBtn = new Button(this);
        startBtn.setText("Start bot");
        Button stopBtn = new Button(this);
        stopBtn.setText("Stop bot");
        Button selftestBtn = new Button(this);
        selftestBtn.setText("Run self-test");
        layout.addView(statusView);
        layout.addView(startBtn);
        layout.addView(stopBtn);
        layout.addView(selftestBtn);
        Button demoBtn = new Button(this);
        demoBtn.setText(DemoMode.isOn(this)
                ? "Widget demo data: ON (made-up) - tap to switch back"
                : "Widget demo data: OFF - tap to show made-up data");
        demoBtn.setOnClickListener(v -> {
            DemoMode.set(this, !DemoMode.isOn(this));
            demoBtn.setText(DemoMode.isOn(this)
                    ? "Widget demo data: ON (made-up) - tap to switch back"
                    : "Widget demo data: OFF - tap to show made-up data");
        });
        layout.addView(demoBtn);
        localControls = new LocalModelControls(this, layout);
        Button noticesBtn = new Button(this);
        noticesBtn.setText("Third-party licenses and notices");
        noticesBtn.setOnClickListener(v -> showThirdPartyNotices());
        layout.addView(noticesBtn);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(layout);
        setContentView(scroll);

        startBtn.setOnClickListener(v -> {
            Intent intent = new Intent(this, BotService.class);
            if (Build.VERSION.SDK_INT >= 26) {
                startForegroundService(intent);
            } else {
                startService(intent);
            }
        });
        stopBtn.setOnClickListener(v ->
                stopService(new Intent(this, BotService.class)));

        // CI/test hook, DEBUG BUILDS ONLY: launching with --ez autostart_bot
        // true starts the bot immediately, through the exact code path of
        // the Start button. The app starts its own service while foreground
        // (same uid), which adb shell's am start-foreground-service cannot
        // do for a non-exported service on API 34+. The BuildConfig.DEBUG
        // gate keeps release builds from honoring the extra: an external
        // app must never be able to start the assistant via this launcher.
        if (BuildConfig.DEBUG && getIntent().getBooleanExtra("autostart_bot", false)) {
            Intent intent = new Intent(this, BotService.class);
            if (Build.VERSION.SDK_INT >= 26) {
                startForegroundService(intent);
            } else {
                startService(intent);
            }
        }
        // Same DEBUG-only gate: --ez autosetup_bot true asks the running
        // bot to configure a throwaway relay account and print its
        // securejoin invite to logcat, so CI can drive a real setup +
        // chat round trip. Ignored by release builds like autostart_bot.
        if (BuildConfig.DEBUG && getIntent().getBooleanExtra("autosetup_bot", false)) {
            new Thread(() -> {
                try {
                    for (int i = 0; i < 90 && !Python.isStarted(); i++) {
                        Thread.sleep(1000);
                    }
                    Python.getInstance().getModule("android_bot")
                            .callAttr("ci_autosetup");
                } catch (Exception ignored) {
                }
            }).start();
        }
        selftestBtn.setOnClickListener(v -> statusView.setText(
                Python.getInstance().getModule("bootstrap")
                        .callAttr("selftest").toString()));

        handler.post(new Runnable() {
            @Override
            public void run() {
                try {
                    statusView.setText("Status: " + Python.getInstance()
                            .getModule("android_bot").callAttr("status"));
                } catch (Exception e) {
                    statusView.setText("Status: unavailable (" + e + ")");
                }
                handler.postDelayed(this, 2000);
            }
        });
    }

    private void showThirdPartyNotices() {
        if (noticesLoading) return;
        noticesLoading = true;
        AlertDialog loading = new AlertDialog.Builder(this)
                .setTitle("Third-party licenses and notices")
                .setMessage("Loading bundled notices...")
                .setCancelable(false).create();
        loading.show();
        new Thread(() -> {
            List<String> pages = null;
            try (InputStream in = getAssets().open("third_party_notices.txt")) {
                pages = NoticePages.read(in, 5000);
            } catch (Exception ignored) {
            }
            final List<String> loadedPages = pages;
            runOnUiThread(() -> {
                noticesLoading = false;
                if (!isFinishing()) {
                    loading.dismiss();
                    if (loadedPages == null || loadedPages.isEmpty()) {
                        new AlertDialog.Builder(this).setTitle("Third-party licenses and notices")
                                .setMessage("Notices are unavailable in this build.")
                                .setPositiveButton("Close", null).show();
                    } else {
                        showNoticePage(loadedPages, 0);
                    }
                }
            });
        }, "denyut-license-notices").start();
    }

    private void showNoticePage(List<String> pages, int initialPage) {
        final int[] current = {initialPage};
        TextView pageNumber = new TextView(this);
        TextView text = new TextView(this);
        text.setTextSize(13);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        text.setPadding(pad, pad, pad, pad);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(text);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.addView(pageNumber);
        content.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, (int) (420 * getResources().getDisplayMetrics().density)));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Third-party licenses and notices")
                .setView(content)
                .setNeutralButton("Previous", null)
                .setNegativeButton("Next", null)
                .setPositiveButton("Close", null).create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                if (current[0] > 0) {
                    current[0]--;
                    renderNoticePage(pages, current[0], pageNumber, text, scroll, dialog);
                }
            });
            dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setOnClickListener(v -> {
                if (current[0] + 1 < pages.size()) {
                    current[0]++;
                    renderNoticePage(pages, current[0], pageNumber, text, scroll, dialog);
                }
            });
            renderNoticePage(pages, current[0], pageNumber, text, scroll, dialog);
        });
        dialog.show();
    }

    private void renderNoticePage(List<String> pages, int index, TextView pageNumber,
                                  TextView text, ScrollView scroll, AlertDialog dialog) {
        pageNumber.setText("Page " + (index + 1) + " of " + pages.size());
        text.setText(pages.get(index));
        scroll.scrollTo(0, 0);
        dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setEnabled(index > 0);
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setEnabled(index + 1 < pages.size());
    }

    @Override protected void onStart() {
        super.onStart();
        localControls.attach();
    }

    @Override protected void onStop() {
        localControls.detach();
        super.onStop();
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == LocalModelControls.PICK_MODEL && result == RESULT_OK
                && data != null && data.getData() != null) {
            LocalModelWork.importSelected(this, data.getData());
        }
    }
}
