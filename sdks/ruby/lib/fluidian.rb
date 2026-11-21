# frozen_string_literal: true

# Fluidian SDK for Ruby (standard library only).
#
#   require "fluidian"
#   app = Fluidian::App.new("Counter")
#   app.view do |ctx|
#     Fluidian::UI.page("Counter",
#       Fluidian::UI.text("Count: #{ctx.state.fetch('count', 0)}"),
#       Fluidian::UI.button("Add one").on("click", "increment"))
#   end
#   app.on("increment") { |ctx, _event| ctx.state["count"] = ctx.state.fetch("count", 0) + 1 }
#   app.run
#
# Run it with `fluidian run -- ruby -Ilib app.rb`.
require "json"

module Fluidian
  VERSION = "1.2.0"
  PROTOCOL = 1

  # Raised by Ctx#ai when a capability cannot be fulfilled.
  class AIError < StandardError; end

  # One element of a scene. Every method returns the node so calls can be chained.
  class Node
    NO_PAYLOAD = Object.new.freeze
    attr_reader :type

    def initialize(type)
      @type = type
      @id = nil
      @props = {}
      @children = []
      @on = {}
      @ai = []
    end

    # Set a property. Values may be any JSON-compatible data.
    def prop(key, value)
      @props[key.to_s] = value
      self
    end

    # Give the node a stable identity (used for events, focus and AI targeting).
    def id(value)
      @id = value
      self
    end

    # Bind a component event to a named action, optionally with a payload.
    def on(event, action, payload = NO_PAYLOAD)
      binding = { "action" => action }
      binding["payload"] = payload unless payload.equal?(NO_PAYLOAD)
      @on[event.to_s] = binding
      self
    end

    # Attach an AI capability to this node.
    def ai(capability, options = nil)
      @ai << { "capability" => capability, "options" => options || {} }
      self
    end

    # Append child nodes; nil entries are skipped.
    def add(*children)
      @children.concat(children.flatten.compact)
      self
    end

    def to_h
      out = { "type" => @type, "props" => @props }
      out["id"] = @id unless @id.nil?
      out["children"] = @children.map(&:to_h) unless @children.empty?
      out["on"] = @on unless @on.empty?
      out["ai"] = @ai unless @ai.empty?
      out
    end
  end

  # An interaction delivered to a handler.
  Event = Struct.new(:name, :target, :value, :form, :payload)
  Session = Struct.new(:state, :route, :locale)

  # Per-session context: state, navigation, notifications and AI.
  class Ctx
    attr_reader :sid, :state

    def initialize(app, sid, session)
      @app = app
      @sid = sid
      @session = session
      @state = session.state
    end

    def route
      @session.route
    end

    def locale
      @session.locale
    end

    def toast(text, tone = "info")
      @app.send_message("t" => "toast", "sid" => @sid, "text" => text, "tone" => tone)
    end

    def navigate(route)
      @session.route = route
      @app.send_message("t" => "navigate", "sid" => @sid, "route" => route)
    end

    # Invoke a capability and wait for its result. Raises AIError on failure.
    def ai(capability, input = {})
      @app.invoke(@sid, capability, input)
    end
  end

  class App
    attr_reader :name, :meta

    def initialize(name, meta = {})
      @name = name
      @meta = meta
      @view = nil
      @handlers = {}
      @actions = []
      @sessions = {}
      @backlog = []
      @rid = 0
      @in = $stdin
      @out = $stdout
      @in.binmode
      @out.binmode
      @out.sync = true
    end

    # Register the block that renders a session's scene.
    def view(&block)
      @view = block
      self
    end

    # Register a handler for a named action.
    def on(action, &block)
      @handlers[action.to_s] = block
      self
    end

    # Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in event.payload.
    def action(name, description, params = {}, &block)
      @actions << { "name" => name, "description" => description, "params" => params || {} }
      on(name, &block)
    end

    def send_message(message)
      @out.write(JSON.generate(message) + "\n")
    end

    def invoke(sid, capability, input)
      @rid += 1
      rid = "r#{@rid}"
      send_message("t" => "ai.invoke", "rid" => rid, "sid" => sid, "capability" => capability, "input" => input || {})
      loop do
        message = read_message
        raise AIError, "engine disconnected" if message.nil?
        if message["t"] == "ai.result" && message["rid"] == rid
          return message["data"] || {} if message["ok"]

          raise AIError, (message["error"] || "capability failed").to_s
        end
        @backlog << message
      end
    end

    # Serve the wire protocol on stdin/stdout until the engine shuts the app down.
    def run
      send_message("t" => "ready", "protocol" => PROTOCOL, "sdk" => "ruby", "sdkVersion" => VERSION,
                   "app" => { "name" => @name, "meta" => @meta }, "actions" => @actions)
      loop do
        message = @backlog.empty? ? read_message : @backlog.shift
        break if message.nil? || !handle(message)
      end
    end

    private

    def read_message
      loop do
        line = @in.gets
        return nil if line.nil?

        line = line.force_encoding("UTF-8").strip
        next if line.empty?

        begin
          message = JSON.parse(line)
          return message if message.is_a?(Hash)
        rescue JSON::ParserError
          next
        end
      end
    end

    def render(sid)
      session = @sessions[sid]
      return if session.nil? || @view.nil?

      send_message("t" => "scene", "sid" => sid, "root" => @view.call(Ctx.new(self, sid, session)).to_h)
    end

    def handle(message)
      sid = message["sid"].to_s
      case message["t"]
      when "open"
        @sessions[sid] = Session.new({}, message["route"] || "/", message["locale"] || "en-US")
        render(sid)
      when "route"
        if @sessions.key?(sid)
          @sessions[sid].route = message["route"] || "/"
          render(sid)
        end
      when "event"
        session = @sessions[sid]
        handler = @handlers[message["name"].to_s]
        if session.nil?
          send_message("t" => "log", "level" => "warn", "message" => "event for unknown session #{sid}")
        elsif handler.nil?
          send_message("t" => "log", "level" => "warn", "message" => "no handler for action #{message['name']}")
        else
          event = Event.new(message["name"], message["target"], message["value"], message["form"] || {}, message["payload"])
          begin
            handler.call(Ctx.new(self, sid, session), event)
          rescue StandardError => e
            send_message("t" => "error", "sid" => sid, "message" => "#{e.class}: #{e.message}")
            return true
          end
          render(sid)
        end
      when "close"
        @sessions.delete(sid)
      when "shutdown"
        return false
      end
      true
    end
  end
end

require_relative "fluidian/ui"
