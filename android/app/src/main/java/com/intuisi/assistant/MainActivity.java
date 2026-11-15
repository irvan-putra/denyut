package com.intuisi.assistant;

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
