--- Fluidian SDK for Lua 5.1+ / LuaJIT (no dependencies).
--
--   local fl = require("fluidian")
--   local ui = fl.ui
--   local app = fl.App("Counter")
--   app:view(function(ctx)
--     return ui.page("Counter",
--       ui.text("Count: " .. (ctx.state.count or 0)),
--       ui.button("Add one"):on("click", "increment"))
--   end)
--   app:on("increment", function(ctx) ctx.state.count = (ctx.state.count or 0) + 1 end)
--   app:run()
--
-- Run it with `fluidian run -- lua5.4 app.lua`.
local Node = require("fluidian_node")
local ui = require("fluidian_ui")

local fl = { VERSION = "1.2.0", Node = Node, ui = ui, null = Node.null, array = Node.array }
local PROTOCOL = 1
local null = Node.null

-- JSON ------------------------------------------------------------------------
local json = {}
local escapes = { ['"'] = '\\"', ["\\"] = "\\\\", ["\b"] = "\\b", ["\f"] = "\\f", ["\n"] = "\\n", ["\r"] = "\\r", ["\t"] = "\\t" }
local math_type = math.type or function(n) return (n % 1 == 0 and n > -2 ^ 53 and n < 2 ^ 53) and "integer" or "float" end

local function encode(v, out)
  local t = type(v)
  if v == null or v == nil then
    out[#out + 1] = "null"
  elseif t == "string" then
    out[#out + 1] = '"' .. v:gsub('[%c"\\]', function(c) return escapes[c] or string.format("\\u%04x", c:byte()) end) .. '"'
  elseif t == "number" then
    if v ~= v or v == math.huge or v == -math.huge then
      out[#out + 1] = "null"
    elseif math_type(v) == "integer" then
      out[#out + 1] = string.format("%d", v)
    else
      local s
      for digits = 15, 17 do
        s = string.format("%." .. digits .. "g", v)
        if tonumber(s) == v then break end
      end
      out[#out + 1] = s
    end
  elseif t == "boolean" then
    out[#out + 1] = v and "true" or "false"
  elseif t == "table" then
    if getmetatable(v) == Node then v = v:to_json() end
    if Node.is_array(v) then
      out[#out + 1] = "["
      for i = 1, #v do
        if i > 1 then out[#out + 1] = "," end
        encode(v[i], out)
      end
      out[#out + 1] = "]"
    else
      out[#out + 1] = "{"
      local first = true
      for key, value in pairs(v) do
        if not first then out[#out + 1] = "," end
        first = false
        encode(tostring(key), out)
        out[#out + 1] = ":"
        encode(value, out)
      end
      out[#out + 1] = "}"
    end
  else
    error("cannot encode a " .. t .. " as JSON")
  end
end

function json.encode(value)
  local out = {}
  encode(value, out)
  return table.concat(out)
end

local function utf8_char(code)
  if code < 0x80 then return string.char(code) end
  if code < 0x800 then return string.char(0xC0 + math.floor(code / 0x40), 0x80 + code % 0x40) end
  if code < 0x10000 then
    return string.char(0xE0 + math.floor(code / 0x1000), 0x80 + math.floor(code / 0x40) % 0x40, 0x80 + code % 0x40)
  end
  return string.char(0xF0 + math.floor(code / 0x40000), 0x80 + math.floor(code / 0x1000) % 0x40,
    0x80 + math.floor(code / 0x40) % 0x40, 0x80 + code % 0x40)
end

local unescapes = { b = "\b", f = "\f", n = "\n", r = "\r", t = "\t", ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
local decode

local function skip(s, i)
  return s:find("[^ \t\r\n]", i) or #s + 1
end

local function decode_string(s, i)
  local parts, j = {}, i + 1
  while true do
    local k = s:find('["\\]', j)
    if not k then error("unterminated string") end
    parts[#parts + 1] = s:sub(j, k - 1)
    if s:sub(k, k) == '"' then return table.concat(parts), k + 1 end
    local c = s:sub(k + 1, k + 1)
    if c == "u" then
      local code = tonumber(s:sub(k + 2, k + 5), 16)
      j = k + 6
      if code >= 0xD800 and code <= 0xDBFF and s:sub(j, j + 1) == "\\u" then
        local low = tonumber(s:sub(j + 2, j + 5), 16)
        if low and low >= 0xDC00 and low <= 0xDFFF then
          code = 0x10000 + (code - 0xD800) * 0x400 + (low - 0xDC00)
          j = j + 6
        end
      end
      parts[#parts + 1] = utf8_char(code)
    else
      parts[#parts + 1] = unescapes[c] or c
      j = k + 2
    end
  end
end

decode = function(s, i)
  i = skip(s, i)
  local c = s:sub(i, i)
  if c == "{" then
    local obj = {}
    i = skip(s, i + 1)
    if s:sub(i, i) == "}" then return obj, i + 1 end
    while true do
      local key
      key, i = decode_string(s, skip(s, i))
      i = skip(s, i)
      if s:sub(i, i) ~= ":" then error("expected ':'") end
      obj[key], i = decode(s, i + 1)
      i = skip(s, i)
      local d = s:sub(i, i)
      if d == "}" then return obj, i + 1 end
      if d ~= "," then error("expected ',' or '}'") end
      i = i + 1
    end
  elseif c == "[" then
    local arr = Node.array({})
    i = skip(s, i + 1)
    if s:sub(i, i) == "]" then return arr, i + 1 end
    while true do
      arr[#arr + 1], i = decode(s, i)
      i = skip(s, i)
      local d = s:sub(i, i)
      if d == "]" then return arr, i + 1 end
      if d ~= "," then error("expected ',' or ']'") end
      i = i + 1
    end
  elseif c == '"' then
    return decode_string(s, i)
  elseif s:sub(i, i + 3) == "true" then
    return true, i + 4
  elseif s:sub(i, i + 4) == "false" then
    return false, i + 5
  elseif s:sub(i, i + 3) == "null" then
    return null, i + 4
  end
  local text = s:match("^-?%d+%.?%d*[eE]?[+-]?%d*", i)
  if not text or text == "" then error("unexpected character at " .. i) end
  local number = tonumber(text)
  if not text:find("[.eE]") and math.tointeger then number = math.tointeger(number) or number end
  return number, i + #text
end

function json.decode(text)
  local ok, value = pcall(decode, text, 1)
  if ok then return value end
  return nil, value
end

fl.json = json

-- Application -----------------------------------------------------------------
local Ctx = {}
Ctx.__index = Ctx

function Ctx:toast(text, tone)
  self._app:_send({ t = "toast", sid = self.sid, text = text, tone = tone or "info" })
end

function Ctx:navigate(route)
  self._session.route = route
  self.route = route
  self._app:_send({ t = "navigate", sid = self.sid, route = route })
end

--- Invoke a capability and wait for its result. Returns `data`, or `nil, message` on failure.
function Ctx:ai(capability, input)
  return self._app:_invoke(self.sid, capability, input or {})
end

local App = {}
App.__index = App

--- Create an application.
function fl.App(name, meta)
  return setmetatable({ name = name, meta = meta or {}, _handlers = {}, _actions = Node.array({}), _sessions = {}, _backlog = {}, _rid = 0 }, App)
end

--- Register the function that renders a session's scene.
function App:view(fn)
  self._view = fn
  return self
end

--- Register a handler for a named action.
function App:on(action, fn)
  self._handlers[action] = fn
  return self
end

--- Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`.
function App:action(name, description, params, fn)
  self._actions[#self._actions + 1] = { name = name, description = description, params = params or {} }
  return self:on(name, fn)
end

function App:_send(message)
  io.stdout:write(json.encode(message), "\n")
  io.stdout:flush()
end

function App:_read()
  while true do
    local line = io.stdin:read("*l")
    if line == nil then return nil end
    if line:find("%S") then
      local message = json.decode(line)
      if type(message) == "table" then return message end
    end
  end
end

function App:_invoke(sid, capability, input)
  self._rid = self._rid + 1
  local rid = "r" .. self._rid
  self:_send({ t = "ai.invoke", rid = rid, sid = sid, capability = capability, input = input })
  while true do
    local message = self:_read()
    if message == nil then return nil, "engine disconnected" end
    if message.t == "ai.result" and message.rid == rid then
      if message.ok == true then return message.data or {} end
      return nil, tostring(message.error or "capability failed")
    end
    self._backlog[#self._backlog + 1] = message
  end
end

function App:_ctx(sid, session)
  return setmetatable({ _app = self, _session = session, sid = sid, state = session.state, route = session.route, locale = session.locale }, Ctx)
end

function App:_render(sid)
  local session = self._sessions[sid]
  if not session or not self._view then return end
  self:_send({ t = "scene", sid = sid, root = self._view(self:_ctx(sid, session)):to_json() })
end

local function value_of(v)
  if v == null then return nil end
  return v
end

function App:_handle(message)
  local sid = tostring(message.sid or "")
  if message.t == "open" then
    self._sessions[sid] = { state = {}, route = value_of(message.route) or "/", locale = value_of(message.locale) or "en-US" }
    self:_render(sid)
  elseif message.t == "route" then
    if self._sessions[sid] then
      self._sessions[sid].route = value_of(message.route) or "/"
      self:_render(sid)
    end
  elseif message.t == "event" then
    local session, handler = self._sessions[sid], self._handlers[message.name]
    if not session then
      self:_send({ t = "log", level = "warn", message = "event for unknown session " .. sid })
    elseif not handler then
      self:_send({ t = "log", level = "warn", message = "no handler for action " .. tostring(message.name) })
    else
      local event = { name = message.name, target = value_of(message.target), value = value_of(message.value),
        form = value_of(message.form) or {}, payload = value_of(message.payload) }
      local ok, err = pcall(handler, self:_ctx(sid, session), event)
      if ok then
        self:_render(sid)
      else
        self:_send({ t = "error", sid = sid, message = tostring(err) })
      end
    end
  elseif message.t == "close" then
    self._sessions[sid] = nil
  elseif message.t == "shutdown" then
    return false
  end
  return true
end

--- Serve the wire protocol on stdin/stdout until the engine shuts the app down.
function App:run()
  self:_send({ t = "ready", protocol = PROTOCOL, sdk = "lua", sdkVersion = fl.VERSION, app = { name = self.name, meta = self.meta }, actions = self._actions })
  while true do
    local message = table.remove(self._backlog, 1) or self:_read()
    if message == nil or not self:_handle(message) then break end
  end
end

return fl
