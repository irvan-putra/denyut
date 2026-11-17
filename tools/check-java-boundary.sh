#!/usr/bin/env bash
# Run from denyut repo root with JDK21 on PATH and ANDROID_HOME set.
# Account-free synthetic Java checks only. No model weights/native initialization.
set -euo pipefail
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
curl -fsSL https://dl.google.com/dl/android/maven2/com/google/ai/edge/litertlm/litertlm-android/0.19.1/litertlm-android-0.19.1.aar -o "$w/litertlm.aar"
curl -fsSL https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-stdlib/2.4.0/kotlin-stdlib-2.4.0.jar -o "$w/kotlin.jar"
curl -fsSL https://repo.maven.apache.org/maven2/org/jetbrains/annotations/26.0.2/annotations-26.0.2.jar -o "$w/annotations.jar"
(cd "$w"; printf '%s\n' '341f66349ac962e0b6733b8da419b045a4834fca2f7db0bd13e049ce1cfcca72  litertlm.aar' 'ccb14ff83fabcb11458b798dbc9824748ccdffeec79c9aba789e6ed1cda86b1c  kotlin.jar' '2037be378980d3ba9333e97955f3b2cde392aa124d04ca73ce2eee6657199297  annotations.jar' | sha256sum -c -; unzip -q litertlm.aar classes.jar)
# The Android stubs provide android.system.Os at compile time only. The harness
# injects a pure-Java rename for successful synthetic imports, so it never calls Android stubs.
cp="$w/classes.jar:$w/kotlin.jar:$w/annotations.jar:$ANDROID_HOME/platforms/android-35/android.jar"
mkdir -p "$w/out"
javac -cp "$cp" -d "$w/out" android/app/src/main/java/com/vanipy/denyut/LocalGemma.java android/app/src/main/java/com/vanipy/denyut/ModelFile.java tests/java/LocalGemmaBoundaryTest.java
java -ea -cp "$w/out:$cp" com.vanipy.denyut.LocalGemmaBoundaryTest
