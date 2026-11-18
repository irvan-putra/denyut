plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

android {
    namespace = "com.vanipy.denyut"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.vanipy.denyut"
        minSdk = 24
        targetSdk = 35
        versionCode = (project.findProperty("versionCode") as String?)?.toInt() ?: 6
        versionName = (project.findProperty("versionName") as String?) ?: "0.7.0"

        ndk {
            // arm64-v8a only (modern mid-range phones are arm64), and CI runs the
            // same APK on an arm64 emulator image. x86_64 is NOT added:
            // deltachat-rpc-server ships no x86_64 Android wheel on PyPI,
            // so a dual-ABI build cannot carry the DeltaChat core.
            abiFilters += listOf("arm64-v8a")
        }
    }

    buildFeatures {
        // BuildConfig is needed for the DEBUG gate on the autostart hook.
        buildConfig = true
    }

    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            all { it.systemProperty("robolectric.graphicsMode", "NATIVE") }
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
            // PINNED matched set (drift broke CI run 43688709457: client
            // 2.58 vs server 2.69 dropped sender.is_verified). deltabot-cli
            // 9.1.0 pulls deltachat2[full], whose "full" extra pins
            // deltachat-rpc-server==2.58.0; all three are pinned so the
            // resolution stays deterministic.
            install("deltabot-cli==9.1.0")
            install("deltachat2==2.58.0")
            // deltachat-rpc-server: PyPI hosts official Android wheels
            // (android_21_arm64_v8a) bundling the chatmail core binary.
            install("deltachat-rpc-server==2.58.0")
        }
    }
}

// Pinned Android runtime only. No model weights or downloader are bundled.
dependencies {
    implementation("com.google.ai.edge.litertlm:litertlm-android:0.19.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.14.1") // test-only, not in the APK
}

// Runtime API is pre-1.0. Review and rebuild on every dependency change.
dependencies {
    constraints {
        implementation("com.google.code.gson:gson:2.14.0") { version { strictly("2.14.0") } }
        implementation("org.jetbrains.kotlin:kotlin-reflect:2.4.0") { version { strictly("2.4.0") } }
        implementation("org.jetbrains.kotlin:kotlin-stdlib:2.4.0") { version { strictly("2.4.0") } }
        implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.11.0") { version { strictly("1.11.0") } }
        implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0") { version { strictly("1.11.0") } }
        implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.11.0") { version { strictly("1.11.0") } }
    }
}
