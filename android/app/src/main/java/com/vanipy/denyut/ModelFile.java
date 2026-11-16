package com.vanipy.denyut;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import android.system.Os;
import java.security.MessageDigest;

/** File-only model import, not a downloader. Caller owns user consent, the
 * selected stream and app-private destination. Explicit 2.59 GB copy, plus
 * temporary space: never auto-import, never run on the UI thread.
 */
public final class ModelFile {
    public static final long EXPECTED_BYTES = 2588147712L;
    public static final String EXPECTED_SHA256 =
            "181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c";
    public interface Progress {
        void update(long bytes) throws IOException;
    }
    private ModelFile() {}

    public static void verify(File file) throws Exception {
        if (!file.isFile() || file.length() != EXPECTED_BYTES)
            throw new IOException("Unexpected model size");
        try (InputStream in = new FileInputStream(file)) {
            if (!EXPECTED_SHA256.equals(digest(in, null, null, EXPECTED_BYTES)))
                throw new IOException("Model integrity check failed");
        }
    }

    /** Leaves a previous good destination untouched if copy/hash verification fails.
     * The source stream is closed by its caller. Caller serializes model imports
     * and ensures the destination is not loaded in a native engine.
     */
    public static void importSelected(InputStream source, File destination) throws Exception {
        importSelected(source, destination, null);
    }

    public static void importSelected(InputStream source, File destination, Progress progress) throws Exception {
        importChecked(source, destination, progress, EXPECTED_BYTES, EXPECTED_SHA256,
                (temporary, target) -> Os.rename(temporary.getAbsolutePath(), target.getAbsolutePath()));
    }

    interface Renamer { void rename(File source, File destination) throws Exception; }
    // Package-only synthetic test seam, production callers cannot choose metadata.
    static void importChecked(InputStream source, File destination, Progress progress,
                              long expectedBytes, String expectedHash, Renamer renamer) throws Exception {
        File directory = destination.getCanonicalFile().getParentFile();
        if (directory == null || (!directory.isDirectory() && !directory.mkdirs()))
            throw new IOException("Model directory unavailable");
        File temporary = File.createTempFile("model-import-", ".part", directory);
        try {
            String hash;
            try (FileOutputStream out = new FileOutputStream(temporary)) {
                hash = digest(source, out, progress, expectedBytes);
                out.getFD().sync();
            }
            if (temporary.length() != expectedBytes || !expectedHash.equals(hash))
                throw new IOException("Model integrity check failed");
            if (progress != null) progress.update(expectedBytes);
            renamer.rename(temporary, destination);
        } finally {
            if (temporary.exists() && !temporary.delete()) temporary.deleteOnExit();
        }
    }

    private static String digest(InputStream in, FileOutputStream out, Progress progress, long expectedBytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[1024 * 1024];
        long count = 0;
        int read;
        while ((read = in.read(buffer)) != -1) {
            count += read;
            if (progress != null) progress.update(count);
            if (count > expectedBytes) throw new IOException("Model exceeds size limit");
            digest.update(buffer, 0, read);
            if (out != null) out.write(buffer, 0, read);
        }
        byte[] hash = digest.digest();
        StringBuilder hex = new StringBuilder();
        for (byte b : hash) hex.append(String.format("%02x", b & 0xff));
        return hex.toString();
    }
}
