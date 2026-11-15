package com.vanipy.denyut;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends Activity {
    private final Handler handler = new Handler();
    private TextView statusView;

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
        setContentView(layout);

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
}
