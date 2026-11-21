package dev.fluidian;

import java.util.Map;

/** An interaction delivered to a handler. */
public final class Event {
    public final String name;
    public final String target;
    public final Object value;
    public final Map<String, Object> form;
    public final Object payload;

    Event(String name, String target, Object value, Map<String, Object> form, Object payload) {
        this.name = name;
        this.target = target;
        this.value = value;
        this.form = form;
        this.payload = payload;
    }

    /** The payload as a JSON object, or an empty map when it is not one. */
    @SuppressWarnings("unchecked")
    public Map<String, Object> payloadMap() {
        return payload instanceof Map ? (Map<String, Object>) payload : new java.util.LinkedHashMap<String, Object>();
    }
}
