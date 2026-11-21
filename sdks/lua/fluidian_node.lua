-- Scene nodes for the Fluidian Lua SDK.
local Node = {}
Node.__index = Node

--- JSON null. Use it where a property must be explicitly null.
Node.null = setmetatable({}, { __tostring = function() return "null" end })
local ARRAY = { __name = "fluidian.array" }
local MISSING = {}

--- Mark a table as a JSON array (needed for empty arrays; non-empty sequences are detected).
function Node.array(t)
  return setmetatable(t or {}, ARRAY)
end

function Node.is_array(t)
  return getmetatable(t) == ARRAY or (next(t) ~= nil and #t > 0)
end

--- Create a node of the given component type.
function Node.new(type)
  return setmetatable({ type = type, _props = {}, _children = {}, _on = {}, _ai = {} }, Node)
end

--- Set a property. Values may be any JSON-compatible data; nil becomes null.
function Node:prop(key, value)
  if value == nil then value = Node.null end
  self._props[key] = value
  return self
end

--- Give the node a stable identity (used for events, focus and AI targeting).
function Node:id(value)
  self._id = value
  return self
end

--- Bind a component event to a named action, optionally with a payload.
function Node:on(event, action, payload)
  local binding = { action = action }
  if payload ~= nil then binding.payload = payload end
  self._on[event] = binding
  return self
end

--- Attach an AI capability to this node.
function Node:ai(capability, options)
  self._ai[#self._ai + 1] = { capability = capability, options = options or {} }
  return self
end

--- Append child nodes; nil entries are skipped.
function Node:add(...)
  local n = select("#", ...)
  for i = 1, n do
    local child = (select(i, ...))
    if child ~= nil then self._children[#self._children + 1] = child end
  end
  return self
end

function Node:to_json()
  local out = { type = self.type, props = self._props }
  if self._id ~= nil then out.id = self._id end
  if #self._children > 0 then
    local kids = Node.array({})
    for i, child in ipairs(self._children) do kids[i] = child:to_json() end
    out.children = kids
  end
  if next(self._on) ~= nil then out.on = self._on end
  if #self._ai > 0 then out.ai = Node.array(self._ai) end
  return out
end

return Node
