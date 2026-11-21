package = "fluidian"
version = "1.2.0-1"
source = { url = "git+https://github.com/fluidian/fluidian.git", tag = "v1.2.0" }
description = {
  summary = "Fluidian SDK for Lua - build AI-native interfaces.",
  license = "Apache-2.0",
}
dependencies = { "lua >= 5.1" }
build = {
  type = "builtin",
  modules = {
    fluidian = "sdks/lua/fluidian.lua",
    fluidian_node = "sdks/lua/fluidian_node.lua",
    fluidian_ui = "sdks/lua/fluidian_ui.lua",
  },
}
