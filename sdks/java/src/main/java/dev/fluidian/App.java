package dev.fluidian;

import java.io.BufferedReader;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;
import java.util.function.Function;

/**
 * A Fluidian application (Java 11+, no dependencies).
 *
 * <pre>{@code
 * App app = new App("Counter");
 * app.view(ctx -> UI.page("Counter",
 *     UI.text("Count: " + ctx.state.getOrDefault("count", 0L)),
 *     UI.button("Add one").on("click", "increment")));
 * app.on("increment", (ctx, ev) -> ctx.state.merge("count", 1L, (a, b) -> (Long) a + (Long) b));
 * app.run();
 * }</pre>
 *
 * Run it with {@code fluidian run -- java -cp out Main}.
 */
public final class App {
    public static final String VERSION = "1.2.0";
    private static final int PROTOCOL = 1;

    static final class Session {
        final Map<String, Object> state = new LinkedHashMap<>();
        String route = "/";
        String locale = "en-US";
    }

    private final String name;
    private final Map<String, Object> meta = new LinkedHashMap<>();
    private Function<Ctx, Node> view;
    private final Map<String, BiConsumer<Ctx, Event>> handlers = new LinkedHashMap<>();
    private final List<Object> actions = new ArrayList<>();
    private final Map<String, Session> sessions = new LinkedHashMap<>();
    private final Deque<Map<String, Object>> backlog = new ArrayDeque<>();
    private int rid;
    private final BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
    private final PrintStream out;

    public App(String name) {
        this.name = name;
        try {
            this.out = new PrintStream(new FileOutputStream(FileDescriptor.out), false, "UTF-8");
        } catch (UnsupportedEncodingException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Register the function that renders a session's scene. */
    public App view(Function<Ctx, Node> fn) {
        this.view = fn;
        return this;
    }

    /** Register a handler for a named action. */
    public App on(String action, BiConsumer<Ctx, Event> fn) {
        handlers.put(action, fn);
        return this;
    }

    /** Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in {@code event.payload}. */
    public App action(String name, String description, Map<String, Object> params, BiConsumer<Ctx, Event> fn) {
        actions.add(J.obj("name", name, "description", description, "params", params == null ? new LinkedHashMap<String, Object>() : params));
        return on(name, fn);
    }

    void send(Map<String, Object> message) {
        out.print(Json.write(message));
        out.print('\n');
        out.flush();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> read() {
        while (true) {
            String line;
            try {
                line = in.readLine();
            } catch (IOException e) {
                return null;
            }
            if (line == null) {
                return null;
            }
            if (line.trim().isEmpty()) {
                continue;
            }
            try {
                Object message = Json.parse(line);
                if (message instanceof Map) {
                    return (Map<String, Object>) message;
                }
            } catch (RuntimeException ignored) {
                // skip malformed lines
            }
        }
    }

    @SuppressWarnings("unchecked")
    Map<String, Object> invoke(String sid, String capability, Map<String, Object> input) {
        String id = "r" + (++rid);
        send(J.obj("t", "ai.invoke", "rid", id, "sid", sid, "capability", capability, "input", input));
        while (true) {
            Map<String, Object> message = read();
            if (message == null) {
                throw new AIException("engine disconnected");
            }
            if ("ai.result".equals(message.get("t")) && id.equals(message.get("rid"))) {
                if (Boolean.TRUE.equals(message.get("ok"))) {
                    Object data = message.get("data");
                    return data instanceof Map ? (Map<String, Object>) data : new LinkedHashMap<String, Object>();
                }
                Object error = message.get("error");
                throw new AIException(error == null ? "capability failed" : error.toString());
            }
            backlog.add(message);
        }
    }

    private static String text(Object value, String fallback) {
        return value instanceof String && !((String) value).isEmpty() ? (String) value : fallback;
    }

    private void render(String sid) {
        Session session = sessions.get(sid);
        if (session == null || view == null) {
            return;
        }
        send(J.obj("t", "scene", "sid", sid, "root", view.apply(new Ctx(this, sid, session)).toJson()));
    }

    @SuppressWarnings("unchecked")
    private boolean handle(Map<String, Object> message) {
        String sid = text(message.get("sid"), "");
        String kind = text(message.get("t"), "");
        if (kind.equals("open")) {
            Session session = new Session();
            session.route = text(message.get("route"), "/");
            session.locale = text(message.get("locale"), "en-US");
            sessions.put(sid, session);
            render(sid);
        } else if (kind.equals("route")) {
            Session session = sessions.get(sid);
            if (session != null) {
                session.route = text(message.get("route"), "/");
                render(sid);
            }
        } else if (kind.equals("event")) {
            String action = text(message.get("name"), "");
            Session session = sessions.get(sid);
            BiConsumer<Ctx, Event> handler = handlers.get(action);
            if (session == null) {
                send(J.obj("t", "log", "level", "warn", "message", "event for unknown session " + sid));
            } else if (handler == null) {
                send(J.obj("t", "log", "level", "warn", "message", "no handler for action " + action));
            } else {
                Object form = message.get("form");
                Event event = new Event(action, text(message.get("target"), null), message.get("value"),
                        form instanceof Map ? (Map<String, Object>) form : new LinkedHashMap<String, Object>(), message.get("payload"));
                try {
                    handler.accept(new Ctx(this, sid, session), event);
                } catch (RuntimeException error) {
                    send(J.obj("t", "error", "sid", sid, "message", error.getClass().getSimpleName() + ": " + error.getMessage()));
                    return true;
                }
                render(sid);
            }
        } else if (kind.equals("close")) {
            sessions.remove(sid);
        } else if (kind.equals("shutdown")) {
            return false;
        }
        return true;
    }

    /** Serve the wire protocol on stdin/stdout until the engine shuts the app down. */
    public void run() {
        send(J.obj("t", "ready", "protocol", PROTOCOL, "sdk", "java", "sdkVersion", VERSION, "app", J.obj("name", name, "meta", meta), "actions", actions));
        while (true) {
            Map<String, Object> message = backlog.isEmpty() ? read() : backlog.poll();
            if (message == null || !handle(message)) {
                break;
            }
        }
    }
}
