plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

android {
    namespace = "com.intuisi.assistant"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.intuisi.assistant"
        minSdk = 24
        targetSdk = 35
        versionCode = 4
        versionName = "0.6.4"

        ndk {
            // arm64-v8a only (modern mid-range phones are arm64), and CI runs the
            // same APK on an arm64 emulator image. x86_64 is NOT added:
            // deltachat-rpc-server ships no x86_64 Android wheel on PyPI,
            // so a dual-ABI build cannot carry the DeltaChat core.
            abiFilters += listOf("arm64-v8a")
        }
    }

    // The rpc-server binary must be extracted to disk at install time so it
    // can be executed from nativeLibraryDir (execve from the app home dir is
    // blocked for targetSdk 29+; embedded-and-extracted is the supported path).
    packaging {
        jniLibs.useLegacyPackaging = true
    }
}

chaquopy {
    defaultConfig {
        // deltachat2 requires Python >= 3.11 (enum.StrEnum).
        version = "3.12"
        // Chaquopy auto-detects a host Python 3.12 from PATH (CI provides
        // one via actions/setup-python). To override locally:
        // buildPython("/path/to/python3.12")
        pip {
            // deltabot-cli: high-level DeltaChat bot framework.
            install("deltabot-cli")
            // deltachat-rpc-server: PyPI hosts official Android wheels
            // (android_21_arm64_v8a) bundling the chatmail core binary.
            install("deltachat-rpc-server")
        }
    }
}
