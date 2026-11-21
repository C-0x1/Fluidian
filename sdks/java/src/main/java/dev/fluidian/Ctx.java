package dev.fluidian;

import java.util.LinkedHashMap;
import java.util.Map;

/** Per-session context: state, navigation, notifications and AI. */
public final class Ctx {
    private final App app;
    private final App.Session session;
    /** Session identifier. */
    public final String sid;
    /** Mutable per-session state. */
    public final Map<String, Object> state;

    Ctx(App app, String sid, App.Session session) {
        this.app = app;
        this.sid = sid;
        this.session = session;
        this.state = session.state;
    }

    public String route() {
        return session.route;
    }

    public String locale() {
        return session.locale;
    }

    public void toast(String text) {
        toast(text, "info");
    }

    public void toast(String text, String tone) {
        app.send(J.obj("t", "toast", "sid", sid, "text", text, "tone", tone));
    }

    public void navigate(String route) {
        session.route = route;
        app.send(J.obj("t", "navigate", "sid", sid, "route", route));
    }

    /** Invoke a capability and wait for its result. Throws {@link AIException} on failure. */
    public Map<String, Object> ai(String capability, Map<String, Object> input) {
        return app.invoke(sid, capability, input == null ? new LinkedHashMap<String, Object>() : input);
    }
}
