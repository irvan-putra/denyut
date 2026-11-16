package com.vanipy.denyut;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Reads the bundled license text and splits it into bounded UI-sized pages.
 * Call read() off the main thread; only the selected page belongs in a TextView.
 */
public final class NoticePages {
    private NoticePages() {}

    public static List<String> read(InputStream in, int maxChars) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int n;
        while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
        return splitText(new String(out.toByteArray(), StandardCharsets.UTF_8), maxChars);
    }

    static List<String> splitText(String text, int maxChars) {
        if (maxChars < 1) throw new IllegalArgumentException("maxChars must be positive");
        List<String> pages = new ArrayList<>();
        if (text.isEmpty()) {
            pages.add("");
            return pages;
        }
        int start = 0;
        while (start < text.length()) {
            int end = Math.min(start + maxChars, text.length());
            if (end < text.length()) {
                int lineBreak = text.lastIndexOf('\n', end - 1);
                if (lineBreak >= start) end = lineBreak + 1;
                if (end < text.length() && end > start
                        && Character.isHighSurrogate(text.charAt(end - 1))
                        && Character.isLowSurrogate(text.charAt(end))) end--;
            }
            if (end <= start) end = Math.min(start + maxChars, text.length());
            pages.add(text.substring(start, end));
            start = end;
        }
        return pages;
    }
}
