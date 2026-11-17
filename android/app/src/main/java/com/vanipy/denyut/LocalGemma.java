package com.vanipy.denyut;

import com.google.ai.edge.litertlm.Backend;
import com.google.ai.edge.litertlm.Contents;
import com.google.ai.edge.litertlm.Conversation;
import com.google.ai.edge.litertlm.ConversationConfig;
import com.google.ai.edge.litertlm.Engine;
import com.google.ai.edge.litertlm.EngineConfig;
import com.google.ai.edge.litertlm.ThinkingConfig;
import java.io.File;
import java.util.Collections;
import java.util.concurrent.locks.ReentrantLock;

/** Optional CPU-only text trial. No downloader, HTTP client, tools or persisted opt-in.
 * Owner UI must call load on a background worker after explicit file selection.
 * Process restart leaves the engine unloaded. No automatic startup in BotService.
 */
public final class LocalGemma {
    private static final ReentrantLock LOCK = new ReentrantLock();
    private static Engine engine;
    private static final boolean ACTIVATION_REVIEWED = false;
    private static volatile String state = "unloaded";
    private static final int MAX_INPUT_CHARS = 1500;
    private LocalGemma() {}

    public static String status() { return state; }

    /** path must be the app-private, verified ModelFile destination. Not a URI/URL. */
    public static void load(String modelPath, String cachePath) throws Exception {
        if (!ACTIVATION_REVIEWED) throw new IllegalStateException("Local activation is gated pending owner UI and runtime review");
        if (!LOCK.tryLock()) throw new IllegalStateException("Local model is busy");
        try {
            if (engine != null) throw new IllegalStateException("Unload model first");
            File file = new File(modelPath);
            state = "verifying";
            try { ModelFile.verify(file); } // exact size + SHA256, no network
            catch (Exception failure) { state = "unloaded"; throw failure; }
            File cache = new File(cachePath);
            if (!cache.isDirectory() && !cache.mkdirs()) {
                state = "unloaded";
                throw new IllegalStateException("Cache unavailable");
            }
            state = "loading";
            initialize(() -> new Engine(new EngineConfig(
                    file.getCanonicalPath(), new Backend.CPU(2, null),
                    null, null, 1024, null, cache.getCanonicalPath())));
        } finally { LOCK.unlock(); }
    }

    interface EngineFactory { Engine create() throws Exception; }
    // Called under LOCK by load. Package-private seam tests constructor failure
    // without model weights. Never invoked by an exported intent/chat command.
    static void initialize(EngineFactory factory) throws Exception {
        Engine candidate = null;
        state = "loading";
        try {
            candidate = factory.create();
            candidate.initialize();
            engine = candidate;
            state = "ready";
        } catch (Throwable failure) {
            if (candidate != null) try { candidate.close(); } catch (Throwable ignored) { }
            state = "unloaded";
            throw new IllegalStateException("Local model load failed");
        }
    }

    /** One stateless request, no tools, no conversation shared between senders.
     * This preparatory bridge deliberately omits prior chat history to keep a
     * predictable small budget. A token/context-limit exception is a local error,
     * never a request to another backend. Invoke away from the Android UI thread.
     */
    public static String complete(String system, String text) {
        if (text == null || system == null || text.length() + system.length() > MAX_INPUT_CHARS)
            throw new IllegalArgumentException("Local request exceeds trial input limit");
        if (!LOCK.tryLock()) throw new IllegalStateException("Local model is busy");
        try {
            if (engine == null) throw new IllegalStateException("Local model is unloaded");
            state = "generating";
            ConversationConfig config = new ConversationConfig(
                    Contents.Companion.of(system), Collections.emptyList(), Collections.emptyList(),
                    null, false, null, Collections.emptyMap(), null, false,
                    128, new ThinkingConfig(false));
            try (Conversation conversation = engine.createConversation(config)) {
                return conversation.sendMessage(text).toString();
            } catch (Throwable failure) {
                throw new IllegalStateException("Local generation failed");
            } finally { state = "ready"; }
        } finally { LOCK.unlock(); }
    }

    /** No forced cancellation or close while native generation is executing.
     * Busy rejection is explicit; a future owner UI must wait/retry, not report
     * unloaded prematurely. There is no proven wall-clock inference timeout yet.
     */
    public static void unload() {
        if (!LOCK.tryLock()) throw new IllegalStateException("Local model is busy");
        try {
            if (engine != null) {
                try { engine.close(); }
                finally { engine = null; state = "unloaded"; }
            }
        } finally { LOCK.unlock(); }
    }
}
