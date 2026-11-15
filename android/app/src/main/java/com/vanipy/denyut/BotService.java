package com.vanipy.denyut;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.IBinder;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;

/**
 * Foreground service running the Denyut DeltaChat bot on a Python thread.
 * A persistent notification keeps Android from killing it; the user can
 * stop it from the app or the notification.
 */
public class BotService extends Service {
    public static final String CHANNEL_ID = "denyut_bot";
    private static final int NOTIFICATION_ID = 1;
    private Thread botThread;

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "Denyut bot", NotificationManager.IMPORTANCE_LOW);
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Intent openApp = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(
                this, 0, openApp, PendingIntent.FLAG_IMMUTABLE);
        Notification notification =
                new Notification.Builder(this, CHANNEL_ID)
                        .setContentTitle("Denyut")
                        .setContentText("Assistant bot is running")
                        .setSmallIcon(android.R.drawable.ic_dialog_info)
                        .setContentIntent(pending)
                        .setOngoing(true)
                        .build();
        startForeground(NOTIFICATION_ID, notification);

        if (botThread == null || !botThread.isAlive()) {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
            }
            File files = getFilesDir();
            String accountsDir = new File(files, "accounts").getAbsolutePath();
            String storeDir = new File(files, "store").getAbsolutePath();
            new File(accountsDir).mkdirs();
            new File(storeDir).mkdirs();
            final String rpcServer;
            try {
                rpcServer = ServerBin.ensure(this);
            } catch (Exception e) {
                throw new RuntimeException("rpc-server missing from native library dir", e);
            }
            botThread = new Thread(() -> Python.getInstance()
                    .getModule("android_bot")
                    .callAttr("serve", accountsDir, storeDir, rpcServer));
            botThread.start();
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        try {
            if (Python.isStarted()) {
                Python.getInstance().getModule("android_bot").callAttr("stop");
            }
        } catch (Exception ignored) {
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
