package dev.fluidian;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Helpers for writing JSON literals in Java source. */
public final class J {
    private J() {}

    /** Build a JSON object from alternating keys and values: {@code J.obj("label", "Save", "count", 3)}. */
    public static Map<String, Object> obj(Object... pairs) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            map.put(String.valueOf(pairs[i]), pairs[i + 1]);
        }
        return map;
    }

    /** Build a JSON array. */
    public static List<Object> arr(Object... items) {
        List<Object> list = new ArrayList<>();
        if (items == null) {
            list.add(null);
            return list;
        }
        for (Object item : items) {
            list.add(item);
        }
        return list;
    }
}
