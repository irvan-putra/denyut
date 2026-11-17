package com.vanipy.denyut;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.nio.file.Files;
import java.util.Arrays;

/** Host boundary checks against actual runtime AAR classes, no native engine
 * initialization or real model. Run with assertions enabled. */
public final class LocalGemmaBoundaryTest {
    public static void main(String[] args) throws Exception {
        boolean assertions = false;
        assert assertions = true;
        if (!assertions) throw new AssertionError("Run boundary harness with java -ea");
        assert "unloaded".equals(LocalGemma.status());
        try { LocalGemma.complete("system", "synthetic"); throw new AssertionError(); }
        catch (IllegalStateException expected) { }
        assert "unloaded".equals(LocalGemma.status());
        try { LocalGemma.complete("", new String(new char[4001])); throw new AssertionError(); }
        catch (IllegalArgumentException expected) { }
        try { LocalGemma.initialize(() -> { throw new IllegalStateException("synthetic constructor failure"); }); throw new AssertionError(); }
        catch (IllegalStateException expected) { }
        assert "unloaded".equals(LocalGemma.status());
        LocalGemma.unload();
        File directory = Files.createTempDirectory("denyut-model-boundary-").toFile();
        File model = new File(directory, "model.litertlm");
        byte[] original = new byte[] {1, 2, 3};
        Files.write(model.toPath(), original);
        try {
            try { ModelFile.verify(model); throw new AssertionError(); }
            catch (java.io.IOException expected) { }
            try { LocalGemma.load(model.getAbsolutePath(), directory.getAbsolutePath()); throw new AssertionError(); }
            catch (IllegalStateException expected) { }
            assert "unloaded".equals(LocalGemma.status());
            try {
                ModelFile.importSelected(new ByteArrayInputStream(new byte[] {4, 5}), model);
                throw new AssertionError();
            } catch (java.io.IOException expected) { }
            assert Arrays.equals(original, Files.readAllBytes(model.toPath()));
            assert directory.listFiles().length == 1; // rejected .part cleaned
            byte[] synthetic = new byte[] {4, 5};
            String syntheticHash = "2fa1b377bf67309f65e5e7bc9d924345ca648dec4e601a398a9cb497dcba3765";
            ModelFile.importChecked(new ByteArrayInputStream(synthetic), model, null,
                    2, syntheticHash, (source, target) -> Files.move(source.toPath(), target.toPath(),
                            java.nio.file.StandardCopyOption.REPLACE_EXISTING));
            assert Arrays.equals(synthetic, Files.readAllBytes(model.toPath()));
            try {
                ModelFile.importChecked(new ByteArrayInputStream(synthetic), model,
                        bytes -> { throw new java.io.IOException("synthetic cancel"); },
                        2, syntheticHash, (source, target) -> { throw new AssertionError("no rename on cancellation"); });
                throw new AssertionError();
            } catch (java.io.IOException expected) { }
            assert Arrays.equals(synthetic, Files.readAllBytes(model.toPath()));
            assert directory.listFiles().length == 1;

        } finally {
            model.delete();
            directory.delete();
        }
        System.out.println("Local model Java boundary checks passed (no weights/native inference)");
    }
}
