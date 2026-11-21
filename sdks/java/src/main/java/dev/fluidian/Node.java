package dev.fluidian;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** One element of a scene. Every method returns the node so calls can be chained. */
public final class Node {
    private final String type;
    private String id;
    private final Map<String, Object> props = new LinkedHashMap<>();
    private final List<Node> children = new ArrayList<>();
    private final Map<String, Object> on = new LinkedHashMap<>();
    private final List<Object> ai = new ArrayList<>();

    public Node(String type) {
        this.type = type;
    }

    /** Set a property. Values may be any JSON-compatible data. */
    public Node prop(String key, Object value) {
        props.put(key, value);
        return this;
    }

    /** Give the node a stable identity (used for events, focus and AI targeting). */
    public Node id(String value) {
        this.id = value;
        return this;
    }

    /** Bind a component event to a named action. */
    public Node on(String event, String action) {
        on.put(event, J.obj("action", action));
        return this;
    }

    /** Bind a component event to a named action with a payload. */
    public Node on(String event, String action, Object payload) {
        on.put(event, J.obj("action", action, "payload", payload));
        return this;
    }

    /** Attach an AI capability to this node. */
    public Node ai(String capability) {
        return ai(capability, null);
    }

    /** Attach an AI capability with options. */
    public Node ai(String capability, Map<String, Object> options) {
        ai.add(J.obj("capability", capability, "options", options == null ? new LinkedHashMap<String, Object>() : options));
        return this;
    }

    /** Append child nodes; null entries are skipped. */
    public Node add(Node... nodes) {
        for (Node node : nodes) {
            if (node != null) {
                children.add(node);
            }
        }
        return this;
    }

    public Map<String, Object> toJson() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("type", type);
        out.put("props", props);
        if (id != null) {
            out.put("id", id);
        }
        if (!children.isEmpty()) {
            List<Object> kids = new ArrayList<>();
            for (Node child : children) {
                kids.add(child.toJson());
            }
            out.put("children", kids);
        }
        if (!on.isEmpty()) {
            out.put("on", on);
        }
        if (!ai.isEmpty()) {
            out.put("ai", ai);
        }
        return out;
    }
}
