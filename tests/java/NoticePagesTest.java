package com.vanipy.denyut;

import java.util.List;

/** Host check that notice pagination preserves all text and bounds each page. */
public final class NoticePagesTest {
    public static void main(String[] args) {
        StringBuilder source = new StringBuilder("a".repeat(63)).append("\uD83C\uDF31\nheader\n");
        for (int i = 0; i < 31; i++) source.append("license line ").append(i).append("\n");
        source.append("x".repeat(1100)).append("\uD83C\uDF31"); // long line and a supplementary character split safely
        String original = source.toString();
        List<String> pages = NoticePages.splitText(original, 64);
        StringBuilder joined = new StringBuilder();
        for (String page : pages) {
            if (page.length() > 64) throw new AssertionError("page exceeds bound");
            if (!page.isEmpty() && Character.isHighSurrogate(page.charAt(page.length() - 1)))
                throw new AssertionError("page ends with an unpaired high surrogate");
            if (!page.isEmpty() && Character.isLowSurrogate(page.charAt(0)))
                throw new AssertionError("page starts with an unpaired low surrogate");
            joined.append(page);
        }
        if (!original.contentEquals(joined)) throw new AssertionError("pagination lost or changed text");
        if (pages.size() < 10) throw new AssertionError("expected multiple bounded pages");
        System.out.println("Notice pagination passed: " + pages.size() + " pages, exact text preserved");
    }
}
