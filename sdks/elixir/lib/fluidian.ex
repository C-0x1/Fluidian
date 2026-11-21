# Fluidian SDK for Elixir (no dependencies).
#
#     alias Fluidian.{App, Ctx, UI}
#
#     App.new("Counter")
#     |> App.view(fn ctx ->
#       UI.page("Counter", [
#         UI.text("Count: #{Ctx.get(ctx, "count", 0)}"),
#         UI.button("Add one") |> Fluidian.Node.on("click", "increment")
#       ])
#     end)
#     |> App.on("increment", fn ctx, _event -> Ctx.put(ctx, "count", Ctx.get(ctx, "count", 0) + 1) end)
#     |> App.run()
#
# Run it with `fluidian run -- elixir app.exs`.

defmodule Fluidian.Json do
  @moduledoc "A small, dependency-free JSON encoder and decoder."

  def encode(value), do: IO.iodata_to_binary(enc(value))

  defp enc(nil), do: "null"
  defp enc(true), do: "true"
  defp enc(false), do: "false"
  defp enc(v) when is_integer(v), do: Integer.to_string(v)
  defp enc(v) when is_float(v), do: Float.to_string(v)
  defp enc(v) when is_binary(v), do: [?", escape(v, []), ?"]
  defp enc(v) when is_atom(v), do: enc(Atom.to_string(v))
  defp enc(%{__struct__: Fluidian.Node} = node), do: enc(Fluidian.Node.to_json(node))
  defp enc(v) when is_list(v), do: [?[, Enum.intersperse(Enum.map(v, &enc/1), ?,), ?]]

  defp enc(v) when is_map(v) do
    pairs = Enum.map(v, fn {key, value} -> [enc(to_string(key)), ?:, enc(value)] end)
    [?{, Enum.intersperse(pairs, ?,), ?}]
  end

  defp escape(<<>>, acc), do: Enum.reverse(acc)
  defp escape(<<?", rest::binary>>, acc), do: escape(rest, ["\\\"" | acc])
  defp escape(<<?\\, rest::binary>>, acc), do: escape(rest, ["\\\\" | acc])
  defp escape(<<?\n, rest::binary>>, acc), do: escape(rest, ["\\n" | acc])
  defp escape(<<?\r, rest::binary>>, acc), do: escape(rest, ["\\r" | acc])
  defp escape(<<?\t, rest::binary>>, acc), do: escape(rest, ["\\t" | acc])

  defp escape(<<c, rest::binary>>, acc) when c < 0x20 do
    hex = c |> Integer.to_string(16) |> String.pad_leading(4, "0")
    escape(rest, ["\\u" <> hex | acc])
  end

  defp escape(<<c, rest::binary>>, acc), do: escape(rest, [c | acc])

  @doc "Decode a JSON document. Returns `{:ok, value}` or `:error`."
  def decode(text) when is_binary(text) do
    try do
      {value, rest} = value(skip(text))
      if skip(rest) == "", do: {:ok, value}, else: :error
    rescue
      _ -> :error
    catch
      _ -> :error
    end
  end

  defp skip(<<c, rest::binary>>) when c in [?\s, ?\t, ?\r, ?\n], do: skip(rest)
  defp skip(rest), do: rest

  defp value(<<"{", rest::binary>>), do: object(skip(rest), %{})
  defp value(<<"[", rest::binary>>), do: array(skip(rest), [])
  defp value(<<?", rest::binary>>), do: string(rest, [])
  defp value(<<"true", rest::binary>>), do: {true, rest}
  defp value(<<"false", rest::binary>>), do: {false, rest}
  defp value(<<"null", rest::binary>>), do: {nil, rest}
  defp value(text), do: number(text)

  defp object(<<"}", rest::binary>>, acc), do: {acc, rest}

  defp object(<<?", rest::binary>>, acc) do
    {key, rest} = string(rest, [])
    <<":", rest::binary>> = skip(rest)
    {val, rest} = value(skip(rest))

    case skip(rest) do
      <<",", rest::binary>> -> object(skip(rest), Map.put(acc, key, val))
      <<"}", rest::binary>> -> {Map.put(acc, key, val), rest}
    end
  end

  defp array(<<"]", rest::binary>>, acc), do: {Enum.reverse(acc), rest}

  defp array(text, acc) do
    {val, rest} = value(text)

    case skip(rest) do
      <<",", rest::binary>> -> array(skip(rest), [val | acc])
      <<"]", rest::binary>> -> {Enum.reverse([val | acc]), rest}
    end
  end

  defp string(<<?", rest::binary>>, acc), do: {IO.iodata_to_binary(Enum.reverse(acc)), rest}

  defp string(<<"\\u", hex::binary-size(4), rest::binary>>, acc) do
    code = String.to_integer(hex, 16)

    case {code, rest} do
      {high, <<"\\u", low_hex::binary-size(4), rest2::binary>>} when high in 0xD800..0xDBFF ->
        low = String.to_integer(low_hex, 16)
        string(rest2, [<<0x10000 + (high - 0xD800) * 0x400 + (low - 0xDC00)::utf8>> | acc])

      _ ->
        string(rest, [<<code::utf8>> | acc])
    end
  end

  defp string(<<"\\", c, rest::binary>>, acc) do
    char =
      case c do
        ?n -> "\n"
        ?t -> "\t"
        ?r -> "\r"
        ?b -> "\b"
        ?f -> "\f"
        other -> <<other>>
      end

    string(rest, [char | acc])
  end

  defp string(<<c, rest::binary>>, acc), do: string(rest, [c | acc])

  defp number(text) do
    {digits, rest} = take_number(text, [])
    if digits == "", do: throw(:invalid)

    if String.contains?(digits, [".", "e", "E"]) do
      {float, ""} = Float.parse(digits)
      {float, rest}
    else
      {String.to_integer(digits), rest}
    end
  end

  defp take_number(<<c, rest::binary>>, acc) when c in ?0..?9 or c in [?-, ?+, ?., ?e, ?E], do: take_number(rest, [c | acc])
  defp take_number(rest, acc), do: {IO.iodata_to_binary(Enum.reverse(acc)), rest}
end

defmodule Fluidian.Node do
  @moduledoc "One element of a scene. Every function returns the node so calls can be piped."
  defstruct type: nil, id: nil, props: %{}, children: [], on: %{}, ai: []

  def new(type), do: %__MODULE__{type: type}

  @doc "Set a property. Values may be any JSON-compatible data."
  def prop(%__MODULE__{} = node, key, value), do: %{node | props: Map.put(node.props, to_string(key), value)}

  @doc "Give the node a stable identity (used for events, focus and AI targeting)."
  def id(%__MODULE__{} = node, value), do: %{node | id: value}

  @doc "Bind a component event to a named action."
  def on(%__MODULE__{} = node, event, action), do: %{node | on: Map.put(node.on, event, %{"action" => action})}

  @doc "Bind a component event to a named action with a payload."
  def on(%__MODULE__{} = node, event, action, payload),
    do: %{node | on: Map.put(node.on, event, %{"action" => action, "payload" => payload})}

  @doc "Attach an AI capability to this node."
  def ai(%__MODULE__{} = node, capability, options \\ %{}),
    do: %{node | ai: node.ai ++ [%{"capability" => capability, "options" => options}]}

  @doc "Append a child node or a list of child nodes; nil entries are skipped."
  def add(%__MODULE__{} = node, children) do
    extra = children |> List.wrap() |> Enum.reject(&is_nil/1)
    %{node | children: node.children ++ extra}
  end

  def to_json(%__MODULE__{} = node) do
    %{"type" => node.type, "props" => node.props}
    |> put_unless(node.id == nil, "id", node.id)
    |> put_unless(node.children == [], "children", Enum.map(node.children, &to_json/1))
    |> put_unless(node.on == %{}, "on", node.on)
    |> put_unless(node.ai == [], "ai", node.ai)
  end

  defp put_unless(map, true, _key, _value), do: map
  defp put_unless(map, false, key, value), do: Map.put(map, key, value)
end

defmodule Fluidian.Event do
  @moduledoc "An interaction delivered to a handler."
  defstruct name: "", target: nil, value: nil, form: %{}, payload: nil
end

defmodule Fluidian.Ctx do
  @moduledoc "Per-session context: state, navigation, notifications and AI."
  defstruct sid: "", state: %{}, route: "/", locale: "en-US"

  def get(%__MODULE__{state: state}, key, default \\ nil), do: Map.get(state, key, default)
  def put(%__MODULE__{} = ctx, key, value), do: %{ctx | state: Map.put(ctx.state, key, value)}
  def has?(%__MODULE__{state: state}, key), do: Map.has_key?(state, key)

  @doc "Show a transient message; returns the context so it can be piped."
  def toast(%__MODULE__{} = ctx, text, tone \\ "info") do
    Fluidian.App.send_message(%{"t" => "toast", "sid" => ctx.sid, "text" => text, "tone" => tone})
    ctx
  end

  @doc "Move the session to another route."
  def navigate(%__MODULE__{} = ctx, route) do
    Fluidian.App.send_message(%{"t" => "navigate", "sid" => ctx.sid, "route" => route})
    %{ctx | route: route}
  end

  @doc "Invoke a capability and wait for its result: `{:ok, data}` or `{:error, message}`."
  def ai(%__MODULE__{} = ctx, capability, input \\ %{}), do: Fluidian.App.invoke(ctx.sid, capability, input)
end

defmodule Fluidian.App do
  @moduledoc "A Fluidian application."
  alias Fluidian.{Ctx, Event, Json, Node}

  @version "1.2.0"
  @protocol 1
  defstruct name: "", meta: %{}, view: nil, handlers: %{}, actions: []

  def new(name, meta \\ %{}), do: %__MODULE__{name: name, meta: meta}

  @doc "Register the function that renders a session's scene."
  def view(%__MODULE__{} = app, fun) when is_function(fun, 1), do: %{app | view: fun}

  @doc "Register a handler for a named action. The handler returns the (possibly updated) context."
  def on(%__MODULE__{} = app, action, fun) when is_function(fun, 2), do: %{app | handlers: Map.put(app.handlers, action, fun)}

  @doc "Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`."
  def action(%__MODULE__{} = app, name, description, params, fun) do
    spec = %{"name" => name, "description" => description, "params" => params || %{}}
    on(%{app | actions: app.actions ++ [spec]}, name, fun)
  end

  @doc false
  def send_message(message), do: IO.binwrite(:stdio, [Json.encode(message), "\n"])

  defp read_message do
    case IO.binread(:stdio, :line) do
      line when is_binary(line) ->
        case String.trim(line) do
          "" ->
            read_message()

          text ->
            case Json.decode(text) do
              {:ok, message} when is_map(message) -> message
              _ -> read_message()
            end
        end

      _ ->
        nil
    end
  end

  @doc false
  def invoke(sid, capability, input) do
    count = (Process.get(:fluidian_rid) || 0) + 1
    Process.put(:fluidian_rid, count)
    rid = "r#{count}"
    send_message(%{"t" => "ai.invoke", "rid" => rid, "sid" => sid, "capability" => capability, "input" => input})
    await(rid)
  end

  defp await(rid) do
    case read_message() do
      nil ->
        {:error, "engine disconnected"}

      %{"t" => "ai.result", "rid" => ^rid} = message ->
        if message["ok"] == true, do: {:ok, message["data"] || %{}}, else: {:error, to_string(message["error"] || "capability failed")}

      other ->
        Process.put(:fluidian_backlog, (Process.get(:fluidian_backlog) || []) ++ [other])
        await(rid)
    end
  end

  defp next_message do
    case Process.get(:fluidian_backlog) || [] do
      [first | rest] ->
        Process.put(:fluidian_backlog, rest)
        first

      [] ->
        read_message()
    end
  end

  defp render(%__MODULE__{view: nil}, _sid, _session), do: :ok

  defp render(app, sid, session) do
    ctx = %Ctx{sid: sid, state: session.state, route: session.route, locale: session.locale}
    send_message(%{"t" => "scene", "sid" => sid, "root" => Node.to_json(app.view.(ctx))})
  end

  defp handle(app, sessions, %{"t" => "open"} = m) do
    sid = to_string(m["sid"])
    session = %{state: %{}, route: m["route"] || "/", locale: m["locale"] || "en-US"}
    render(app, sid, session)
    {:cont, Map.put(sessions, sid, session)}
  end

  defp handle(app, sessions, %{"t" => "route"} = m) do
    sid = to_string(m["sid"])

    case sessions do
      %{^sid => session} ->
        session = %{session | route: m["route"] || "/"}
        render(app, sid, session)
        {:cont, Map.put(sessions, sid, session)}

      _ ->
        {:cont, sessions}
    end
  end

  defp handle(app, sessions, %{"t" => "event"} = m) do
    sid = to_string(m["sid"])
    name = to_string(m["name"])
    session = sessions[sid]
    handler = app.handlers[name]

    cond do
      session == nil ->
        send_message(%{"t" => "log", "level" => "warn", "message" => "event for unknown session #{sid}"})
        {:cont, sessions}

      handler == nil ->
        send_message(%{"t" => "log", "level" => "warn", "message" => "no handler for action #{name}"})
        {:cont, sessions}

      true ->
        ctx = %Ctx{sid: sid, state: session.state, route: session.route, locale: session.locale}
        event = %Event{name: name, target: m["target"], value: m["value"], form: m["form"] || %{}, payload: m["payload"]}

        try do
          session =
            case handler.(ctx, event) do
              %Ctx{} = updated -> %{session | state: updated.state, route: updated.route}
              _ -> session
            end

          render(app, sid, session)
          {:cont, Map.put(sessions, sid, session)}
        rescue
          error ->
            send_message(%{"t" => "error", "sid" => sid, "message" => "#{inspect(error.__struct__)}: #{Exception.message(error)}"})
            {:cont, sessions}
        end
    end
  end

  defp handle(_app, sessions, %{"t" => "close"} = m), do: {:cont, Map.delete(sessions, to_string(m["sid"]))}
  defp handle(_app, sessions, %{"t" => "shutdown"}), do: {:halt, sessions}
  defp handle(_app, sessions, _other), do: {:cont, sessions}

  defp loop(app, sessions) do
    case next_message() do
      nil ->
        :ok

      message ->
        case handle(app, sessions, message) do
          {:cont, sessions} -> loop(app, sessions)
          {:halt, _} -> :ok
        end
    end
  end

  @doc "Serve the wire protocol on stdin/stdout until the engine shuts the app down."
  def run(%__MODULE__{} = app) do
    # Treat stdio as raw bytes: the protocol is UTF-8 JSON and must not be re-encoded.
    :io.setopts(:standard_io, [:binary, {:encoding, :latin1}])

    send_message(%{
      "t" => "ready", "protocol" => @protocol, "sdk" => "elixir", "sdkVersion" => @version,
      "app" => %{"name" => app.name, "meta" => app.meta}, "actions" => app.actions
    })

    loop(app, %{})
  end
end
