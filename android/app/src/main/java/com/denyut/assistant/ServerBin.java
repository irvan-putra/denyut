package com.denyut.assistant;

import android.content.Context;

import java.io.File;

/**
 * Locates the bundled deltachat-rpc-server binary.
 *
 * Apps targeting Android 10 (API 29) or higher cannot execve() files
 * from the writable app home directory (W^X policy, documented in
 * "Behavior changes: apps targeting API 29+"). The binary is therefore
 * shipped inside the APK as a native library named to match the
 * lib<name>.so pattern (jniLibs/arm64-v8a/librpcserver.so, fetched and
 * sha256-verified by tools/fetch_rpc_server.py) and executed in place
 * from the extracted native library directory. This requires
 * android:extractNativeLibs="true" so the file exists on disk rather
 * than only inside the APK.
 */
final class ServerBin {
    private static final String LIB_NAME = "librpcserver.so";

    private ServerBin() {}

    static synchronized String ensure(Context context) throws SecurityException {
        File exe = new File(context.getApplicationInfo().nativeLibraryDir, LIB_NAME);
        if (!exe.exists()) {
            throw new SecurityException("rpc-server not extracted at " + exe.getAbsolutePath()
                    + " (extractNativeLibs disabled?)");
        }
        if (!exe.canExecute()) {
            throw new SecurityException("rpc-server not executable at " + exe.getAbsolutePath());
        }
        return exe.getAbsolutePath();
    }
}
