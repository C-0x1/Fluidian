// Fluidian SDK for Kotlin. No dependencies beyond the Kotlin standard library.
package dev.fluidian

import java.io.BufferedReader
import java.io.FileDescriptor
import java.io.FileOutputStream
import java.io.InputStreamReader
import java.io.PrintStream
import java.util.ArrayDeque

/** Thrown by [Ctx.ai] when a capability cannot be fulfilled. */
class AIException(message: String) : RuntimeException(message)

/** A small JSON reader and writer. */
object Json {
    /** Serialise maps, iterables, strings, numbers, booleans, nulls and nodes. */
    fun write(value: Any?): String {
        val out = StringBuilder(256)
        write(value, out)
        return out.toString()
    }

    /** Parse a document into maps, lists, strings, longs, doubles, booleans and nulls. */
    fun parse(text: String): Any? {
        val reader = Reader(text)
        val value = reader.value()
        reader.skip()
        if (reader.pos != text.length) throw IllegalArgumentException("unexpected trailing characters at ${reader.pos}")
        return value
    }

    private fun write(value: Any?, out: StringBuilder) {
        when (value) {
            null -> out.append("null")
            is String -> string(value, out)
            is Boolean -> out.append(value.toString())
            is Double -> out.append(if (value.isNaN() || value.isInfinite()) "null" else value.toString())
            is Float -> write(value.toDouble(), out)
            is Number -> out.append(value.toString())
            is Node -> write(value.toJson(), out)
            is Map<*, *> -> {
                out.append('{')
                var first = true
                for ((key, item) in value) {
                    if (!first) out.append(',')
                    first = false
                    string(key.toString(), out)
                    out.append(':')
                    write(item, out)
                }
                out.append('}')
            }
            is Iterable<*> -> {
                out.append('[')
                var first = true
                for (item in value) {
                    if (!first) out.append(',')
                    first = false
                    write(item, out)
                }
                out.append(']')
            }
            is Array<*> -> write(value.toList(), out)
            else -> string(value.toString(), out)
        }
    }

    private fun string(s: String, out: StringBuilder) {
        out.append('"')
        for (c in s) {
            when {
                c == '"' -> out.append("\\\"")
                c == '\\' -> out.append("\\\\")
                c == '\n' -> out.append("\\n")
                c == '\r' -> out.append("\\r")
                c == '\t' -> out.append("\\t")
                c < ' ' -> out.append(String.format("\\u%04x", c - '\u0000'))
                else -> out.append(c)
            }
        }
        out.append('"')
    }

    private class Reader(val text: String) {
        var pos = 0

        fun skip() {
            while (pos < text.length && text[pos].isWhitespace()) pos++
        }

        fun expect(c: Char) {
            if (pos >= text.length || text[pos] != c) throw IllegalArgumentException("expected '$c' at $pos")
            pos++
        }

        fun value(): Any? {
            skip()
            if (pos >= text.length) throw IllegalArgumentException("unexpected end of input")
            val c = text[pos]
            if (c == '{') {
                val map = LinkedHashMap<String, Any?>()
                pos++
                skip()
                if (text[pos] == '}') {
                    pos++
                    return map
                }
                while (true) {
                    skip()
                    val key = string()
                    skip()
                    expect(':')
                    map[key] = value()
                    skip()
                    if (text[pos] == ',') {
                        pos++
                    } else {
                        expect('}')
                        return map
                    }
                }
            }
            if (c == '[') {
                val list = ArrayList<Any?>()
                pos++
                skip()
                if (text[pos] == ']') {
                    pos++
                    return list
                }
                while (true) {
                    list.add(value())
                    skip()
                    if (text[pos] == ',') {
                        pos++
                    } else {
                        expect(']')
                        return list
                    }
                }
            }
            if (c == '"') return string()
            if (text.startsWith("true", pos)) {
                pos += 4
                return true
            }
            if (text.startsWith("false", pos)) {
                pos += 5
                return false
            }
            if (text.startsWith("null", pos)) {
                pos += 4
                return null
            }
            val start = pos
            var real = false
            while (pos < text.length && "+-0123456789.eE".indexOf(text[pos]) >= 0) {
                val d = text[pos++]
                if (d == '.' || d == 'e' || d == 'E') real = true
            }
            val number = text.substring(start, pos)
            if (number.isEmpty()) throw IllegalArgumentException("unexpected character '$c' at $pos")
            if (real) return number.toDouble()
            return number.toLongOrNull() ?: number.toDouble()
        }

        fun string(): String {
            expect('"')
            val out = StringBuilder()
            while (true) {
                val c = text[pos++]
                if (c == '"') return out.toString()
                if (c != '\\') {
                    out.append(c)
                    continue
                }
                val e = text[pos++]
                when (e) {
                    'n' -> out.append('\n')
                    't' -> out.append('\t')
                    'r' -> out.append('\r')
                    'b' -> out.append('\b')
                    'f' -> out.append('\u000C')
                    'u' -> {
                        out.append(Integer.parseInt(text.substring(pos, pos + 4), 16).toChar())
                        pos += 4
                    }
                    else -> out.append(e)
                }
            }
        }
    }
}

/** One element of a scene. Every method returns the node so calls can be chained. */
class Node(private val type: String) {
    private var id: String? = null
    private val props = LinkedHashMap<String, Any?>()
    private val children = ArrayList<Node>()
    private val on = LinkedHashMap<String, Any?>()
    private val ai = ArrayList<Any?>()

    /** Set a property. Values may be any JSON-compatible data. */
    fun prop(key: String, value: Any?): Node {
        props[key] = value
        return this
    }

    /** Give the node a stable identity (used for events, focus and AI targeting). */
    fun id(value: String): Node {
        id = value
        return this
    }

    /** Bind a component event to a named action, optionally with a payload. */
    @JvmOverloads
    fun on(event: String, action: String, payload: Any? = null): Node {
        val binding = LinkedHashMap<String, Any?>()
        binding["action"] = action
        if (payload != null) binding["payload"] = payload
        on[event] = binding
        return this
    }

    /** Attach an AI capability to this node. */
    @JvmOverloads
    fun ai(capability: String, options: Map<String, Any?>? = null): Node {
        val entry = LinkedHashMap<String, Any?>()
        entry["capability"] = capability
        entry["options"] = options ?: LinkedHashMap<String, Any?>()
        ai.add(entry)
        return this
    }

    /** Append child nodes; null entries are skipped. */
    fun add(vararg nodes: Node?): Node {
        for (node in nodes) if (node != null) children.add(node)
        return this
    }

    fun toJson(): Map<String, Any?> {
        val out = LinkedHashMap<String, Any?>()
        out["type"] = type
        out["props"] = props
        if (id != null) out["id"] = id
        if (children.isNotEmpty()) out["children"] = children.map { it.toJson() }
        if (on.isNotEmpty()) out["on"] = on
        if (ai.isNotEmpty()) out["ai"] = ai
        return out
    }
}

/** An interaction delivered to a handler. */
class Event internal constructor(
    val name: String,
    val target: String?,
    val value: Any?,
    val form: Map<String, Any?>,
    val payload: Any?
) {
    /** The payload as a JSON object, or an empty map when it is not one. */
    @Suppress("UNCHECKED_CAST")
    val payloadMap: Map<String, Any?>
        get() = (payload as? Map<String, Any?>) ?: emptyMap()
}

internal class Session {
    val state = LinkedHashMap<String, Any?>()
    var route = "/"
    var locale = "en-US"
}

/** Per-session context: state, navigation, notifications and AI. */
class Ctx internal constructor(private val app: App, val sid: String, private val session: Session) {
    /** Mutable per-session state. */
    val state: MutableMap<String, Any?> get() = session.state
    val route: String get() = session.route
    val locale: String get() = session.locale

    @JvmOverloads
    fun toast(text: String, tone: String = "info") {
        app.send(mapOf("t" to "toast", "sid" to sid, "text" to text, "tone" to tone))
    }

    fun navigate(route: String) {
        session.route = route
        app.send(mapOf("t" to "navigate", "sid" to sid, "route" to route))
    }

    /** Invoke a capability and wait for its result. Throws [AIException] on failure. */
    @JvmOverloads
    fun ai(capability: String, input: Map<String, Any?> = emptyMap()): Map<String, Any?> = app.invoke(sid, capability, input)
}

/**
 * A Fluidian application.
 *
 * ```kotlin
 * fun main() {
 *     val app = App("Counter")
 *     app.view { ctx -> UI.page("Counter",
 *         UI.text("Count: ${ctx.state["count"] ?: 0}"),
 *         UI.button("Add one").on("click", "increment")) }
 *     app.on("increment") { ctx, _ -> ctx.state["count"] = ((ctx.state["count"] as? Long) ?: 0L) + 1 }
 *     app.run()
 * }
 * ```
 *
 * Run it with `fluidian run -- java -jar counter.jar`.
 */
class App(private val name: String) {
    private var view: ((Ctx) -> Node)? = null
    private val handlers = LinkedHashMap<String, (Ctx, Event) -> Unit>()
    private val actions = ArrayList<Any?>()
    private val sessions = LinkedHashMap<String, Session>()
    private val backlog = ArrayDeque<Map<String, Any?>>()
    private var rid = 0
    private val input = BufferedReader(InputStreamReader(System.`in`, Charsets.UTF_8))
    private val output = PrintStream(FileOutputStream(FileDescriptor.out), false, "UTF-8")

    /** Register the function that renders a session's scene. */
    fun view(fn: (Ctx) -> Node): App {
        view = fn
        return this
    }

    /** Register a handler for a named action. */
    fun on(action: String, fn: (Ctx, Event) -> Unit): App {
        handlers[action] = fn
        return this
    }

    /** Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`. */
    fun action(name: String, description: String, params: Map<String, Any?>, fn: (Ctx, Event) -> Unit): App {
        actions.add(mapOf("name" to name, "description" to description, "params" to params))
        return on(name, fn)
    }

    internal fun send(message: Map<String, Any?>) {
        output.print(Json.write(message))
        output.print('\n')
        output.flush()
    }

    @Suppress("UNCHECKED_CAST")
    private fun read(): Map<String, Any?>? {
        while (true) {
            val line = input.readLine() ?: return null
            if (line.isBlank()) continue
            try {
                val message = Json.parse(line)
                if (message is Map<*, *>) return message as Map<String, Any?>
            } catch (ignored: RuntimeException) {
                // skip malformed lines
            }
        }
    }

    @Suppress("UNCHECKED_CAST")
    internal fun invoke(sid: String, capability: String, input: Map<String, Any?>): Map<String, Any?> {
        rid += 1
        val id = "r$rid"
        send(mapOf("t" to "ai.invoke", "rid" to id, "sid" to sid, "capability" to capability, "input" to input))
        while (true) {
            val message = read() ?: throw AIException("engine disconnected")
            if (message["t"] == "ai.result" && message["rid"] == id) {
                if (message["ok"] == true) return (message["data"] as? Map<String, Any?>) ?: emptyMap()
                throw AIException((message["error"] ?: "capability failed").toString())
            }
            backlog.add(message)
        }
    }

    private fun text(value: Any?, fallback: String): String = if (value is String && value.isNotEmpty()) value else fallback

    private fun render(sid: String) {
        val session = sessions[sid] ?: return
        val fn = view ?: return
        send(mapOf("t" to "scene", "sid" to sid, "root" to fn(Ctx(this, sid, session)).toJson()))
    }

    @Suppress("UNCHECKED_CAST")
    private fun handle(message: Map<String, Any?>): Boolean {
        val sid = text(message["sid"], "")
        when (text(message["t"], "")) {
            "open" -> {
                val session = Session()
                session.route = text(message["route"], "/")
                session.locale = text(message["locale"], "en-US")
                sessions[sid] = session
                render(sid)
            }
            "route" -> {
                val session = sessions[sid]
                if (session != null) {
                    session.route = text(message["route"], "/")
                    render(sid)
                }
            }
            "event" -> {
                val action = text(message["name"], "")
                val session = sessions[sid]
                val handler = handlers[action]
                if (session == null) {
                    send(mapOf("t" to "log", "level" to "warn", "message" to "event for unknown session $sid"))
                } else if (handler == null) {
                    send(mapOf("t" to "log", "level" to "warn", "message" to "no handler for action $action"))
                } else {
                    val form = (message["form"] as? Map<String, Any?>) ?: emptyMap()
                    val event = Event(action, message["target"] as? String, message["value"], form, message["payload"])
                    try {
                        handler(Ctx(this, sid, session), event)
                    } catch (error: RuntimeException) {
                        send(mapOf("t" to "error", "sid" to sid, "message" to "${error.javaClass.simpleName}: ${error.message}"))
                        return true
                    }
                    render(sid)
                }
            }
            "close" -> sessions.remove(sid)
            "shutdown" -> return false
        }
        return true
    }

    /** Serve the wire protocol on stdin/stdout until the engine shuts the app down. */
    fun run() {
        send(mapOf(
            "t" to "ready", "protocol" to PROTOCOL, "sdk" to "kotlin", "sdkVersion" to VERSION,
            "app" to mapOf("name" to name, "meta" to emptyMap<String, Any?>()), "actions" to actions
        ))
        while (true) {
            val message = (if (backlog.isEmpty()) read() else backlog.poll()) ?: break
            if (!handle(message)) break
        }
    }

    companion object {
        const val VERSION = "1.2.0"
        private const val PROTOCOL = 1
    }
}
