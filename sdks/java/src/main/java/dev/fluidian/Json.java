package dev.fluidian;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A small, dependency-free JSON reader and writer. */
public final class Json {
    private final String text;
    private int pos;

    private Json(String text) {
        this.text = text;
    }

    /** Parse a JSON document into maps, lists, strings, longs, doubles, booleans and nulls. */
    public static Object parse(String text) {
        Json reader = new Json(text);
        Object value = reader.value();
        reader.skip();
        if (reader.pos != text.length()) {
            throw new IllegalArgumentException("unexpected trailing characters at " + reader.pos);
        }
        return value;
    }

    /** Serialise a value built from maps, collections, strings, numbers, booleans, nulls and nodes. */
    public static String write(Object value) {
        StringBuilder out = new StringBuilder(256);
        write(value, out);
        return out.toString();
    }

    private static void write(Object value, StringBuilder out) {
        if (value == null) {
            out.append("null");
        } else if (value instanceof String) {
            string((String) value, out);
        } else if (value instanceof Boolean) {
            out.append(value.toString());
        } else if (value instanceof Double || value instanceof Float) {
            double d = ((Number) value).doubleValue();
            out.append(Double.isNaN(d) || Double.isInfinite(d) ? "null" : Double.toString(d));
        } else if (value instanceof Number) {
            out.append(value.toString());
        } else if (value instanceof Node) {
            write(((Node) value).toJson(), out);
        } else if (value instanceof Map) {
            out.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                if (!first) {
                    out.append(',');
                }
                first = false;
                string(String.valueOf(entry.getKey()), out);
                out.append(':');
                write(entry.getValue(), out);
            }
            out.append('}');
        } else if (value instanceof Collection) {
            out.append('[');
            boolean first = true;
            for (Object item : (Collection<?>) value) {
                if (!first) {
                    out.append(',');
                }
                first = false;
                write(item, out);
            }
            out.append(']');
        } else if (value instanceof Object[]) {
            write(java.util.Arrays.asList((Object[]) value), out);
        } else {
            string(value.toString(), out);
        }
    }

    private static void string(String s, StringBuilder out) {
        out.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        out.append('"');
    }

    private void skip() {
        while (pos < text.length() && Character.isWhitespace(text.charAt(pos))) {
            pos++;
        }
    }

    private Object value() {
        skip();
        if (pos >= text.length()) {
            throw new IllegalArgumentException("unexpected end of input");
        }
        char c = text.charAt(pos);
        if (c == '{') {
            Map<String, Object> map = new LinkedHashMap<>();
            pos++;
            skip();
            if (text.charAt(pos) == '}') {
                pos++;
                return map;
            }
            while (true) {
                skip();
                String key = readString();
                skip();
                expect(':');
                map.put(key, value());
                skip();
                if (text.charAt(pos) == ',') {
                    pos++;
                } else {
                    expect('}');
                    return map;
                }
            }
        }
        if (c == '[') {
            List<Object> list = new ArrayList<>();
            pos++;
            skip();
            if (text.charAt(pos) == ']') {
                pos++;
                return list;
            }
            while (true) {
                list.add(value());
                skip();
                if (text.charAt(pos) == ',') {
                    pos++;
                } else {
                    expect(']');
                    return list;
                }
            }
        }
        if (c == '"') {
            return readString();
        }
        if (text.startsWith("true", pos)) {
            pos += 4;
            return Boolean.TRUE;
        }
        if (text.startsWith("false", pos)) {
            pos += 5;
            return Boolean.FALSE;
        }
        if (text.startsWith("null", pos)) {
            pos += 4;
            return null;
        }
        int start = pos;
        boolean real = false;
        while (pos < text.length() && "+-0123456789.eE".indexOf(text.charAt(pos)) >= 0) {
            char d = text.charAt(pos++);
            real |= d == '.' || d == 'e' || d == 'E';
        }
        String number = text.substring(start, pos);
        if (number.isEmpty()) {
            throw new IllegalArgumentException("unexpected character '" + c + "' at " + pos);
        }
        if (real) {
            return Double.valueOf(number);
        }
        try {
            return Long.valueOf(number);
        } catch (NumberFormatException e) {
            return Double.valueOf(number);
        }
    }

    private void expect(char c) {
        if (pos >= text.length() || text.charAt(pos) != c) {
            throw new IllegalArgumentException("expected '" + c + "' at " + pos);
        }
        pos++;
    }

    private String readString() {
        expect('"');
        StringBuilder out = new StringBuilder();
        while (true) {
            char c = text.charAt(pos++);
            if (c == '"') {
                return out.toString();
            }
            if (c != '\\') {
                out.append(c);
                continue;
            }
            char e = text.charAt(pos++);
            switch (e) {
                case 'n': out.append('\n'); break;
                case 't': out.append('\t'); break;
                case 'r': out.append('\r'); break;
                case 'b': out.append('\b'); break;
                case 'f': out.append('\f'); break;
                case 'u':
                    out.append((char) Integer.parseInt(text.substring(pos, pos + 4), 16));
                    pos += 4;
                    break;
                default: out.append(e);
            }
        }
    }
}
