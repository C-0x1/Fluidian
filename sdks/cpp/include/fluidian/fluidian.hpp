// Fluidian SDK for C++17. Header-only, no dependencies.
//
//   #include <fluidian/fluidian.hpp>
//   using namespace fluidian;
//
//   int main() {
//     App app("Counter");
//     app.view([](Ctx& ctx) {
//       return ui::page("Counter", {
//         ui::text("Count: " + std::to_string(ctx.state.get("count").as_int())),
//         ui::button("Add one").on("click", "increment"),
//       });
//     });
//     app.on("increment", [](Ctx& ctx, const Event&) {
//       ctx.state.set("count", ctx.state.get("count").as_int() + 1);
//     });
//     app.run();
//   }
//
// Run it with `fluidian run -- ./counter`.
#pragma once

#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <functional>
#include <initializer_list>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace fluidian {

constexpr const char* VERSION = "1.2.0";
constexpr int PROTOCOL = 1;

class Node;

/// A JSON value. Objects keep their insertion order.
class Json {
 public:
  enum class Type { Null, Bool, Int, Num, Str, Arr, Obj };
  using Member = std::pair<std::string, Json>;

  Json() = default;
  Json(std::nullptr_t) {}
  Json(bool v) : type_(Type::Bool), bool_(v) {}
  Json(int v) : type_(Type::Int), int_(v) {}
  Json(long v) : type_(Type::Int), int_(v) {}
  Json(long long v) : type_(Type::Int), int_(v) {}
  Json(unsigned v) : type_(Type::Int), int_(static_cast<long long>(v)) {}
  Json(unsigned long v) : type_(Type::Int), int_(static_cast<long long>(v)) {}
  Json(unsigned long long v) : type_(Type::Int), int_(static_cast<long long>(v)) {}
  Json(double v) : type_(Type::Num), num_(v) {}
  Json(const char* v) : type_(Type::Str), str_(v ? v : "") {}
  Json(const std::string& v) : type_(Type::Str), str_(v) {}
  Json(std::string&& v) : type_(Type::Str), str_(std::move(v)) {}
  Json(const Node& node);

  /// Build an array: Json::array({"a", 2, true}).
  static Json array(std::initializer_list<Json> items = {}) {
    Json out;
    out.type_ = Type::Arr;
    out.arr_.assign(items.begin(), items.end());
    return out;
  }

  /// Build an array from a vector.
  static Json list(std::vector<Json> items) {
    Json out;
    out.type_ = Type::Arr;
    out.arr_ = std::move(items);
    return out;
  }

  /// Build an object: Json::object({{"label", "Save"}, {"count", 3}}).
  static Json object(std::initializer_list<Member> members = {}) {
    Json out;
    out.type_ = Type::Obj;
    out.obj_.assign(members.begin(), members.end());
    return out;
  }

  Type type() const { return type_; }
  bool is_null() const { return type_ == Type::Null; }
  bool is_bool() const { return type_ == Type::Bool; }
  bool is_number() const { return type_ == Type::Int || type_ == Type::Num; }
  bool is_string() const { return type_ == Type::Str; }
  bool is_array() const { return type_ == Type::Arr; }
  bool is_object() const { return type_ == Type::Obj; }

  bool as_bool(bool fallback = false) const { return type_ == Type::Bool ? bool_ : fallback; }

  long long as_int(long long fallback = 0) const {
    if (type_ == Type::Int) return int_;
    if (type_ == Type::Num) return static_cast<long long>(num_);
    return fallback;
  }

  double as_double(double fallback = 0) const {
    if (type_ == Type::Num) return num_;
    if (type_ == Type::Int) return static_cast<double>(int_);
    return fallback;
  }

  /// The string value, or the fallback for anything that is not a string.
  std::string as_string(const std::string& fallback = "") const { return type_ == Type::Str ? str_ : fallback; }

  /// Text for display: strings as they are, everything else as JSON.
  std::string str() const { return type_ == Type::Str ? str_ : dump(); }

  /// Member of an object, or null when absent.
  const Json& get(const std::string& key) const {
    if (type_ == Type::Obj) {
      for (const Member& member : obj_) {
        if (member.first == key) return member.second;
      }
    }
    return null();
  }

  bool has(const std::string& key) const {
    if (type_ != Type::Obj) return false;
    for (const Member& member : obj_) {
      if (member.first == key) return true;
    }
    return false;
  }

  /// Insert or replace a member. Turns anything that is not an object into one.
  Json& set(const std::string& key, Json value) {
    if (type_ != Type::Obj) {
      *this = object();
    }
    for (Member& member : obj_) {
      if (member.first == key) {
        member.second = std::move(value);
        return *this;
      }
    }
    obj_.emplace_back(key, std::move(value));
    return *this;
  }

  void erase(const std::string& key) {
    for (std::size_t i = 0; i < obj_.size(); ++i) {
      if (obj_[i].first == key) {
        obj_.erase(obj_.begin() + static_cast<std::ptrdiff_t>(i));
        return;
      }
    }
  }

  /// Element of an array, or null when out of range.
  const Json& at(std::size_t index) const { return type_ == Type::Arr && index < arr_.size() ? arr_[index] : null(); }

  /// Append to an array. Turns anything that is not an array into one.
  Json& push(Json value) {
    if (type_ != Type::Arr) {
      *this = array();
    }
    arr_.push_back(std::move(value));
    return *this;
  }

  std::size_t size() const { return type_ == Type::Arr ? arr_.size() : type_ == Type::Obj ? obj_.size() : 0; }
  const std::vector<Json>& items() const { return arr_; }
  const std::vector<Member>& members() const { return obj_; }

  /// Serialise to compact JSON text.
  std::string dump() const {
    std::string out;
    write(out);
    return out;
  }

  /// Parse JSON text. Throws std::runtime_error on malformed input.
  static Json parse(const std::string& text);

 private:
  static const Json& null() {
    static const Json value;
    return value;
  }

  static void write_string(const std::string& s, std::string& out) {
    out += '"';
    for (unsigned char c : s) {
      switch (c) {
        case '"': out += "\\\""; break;
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        default:
          if (c < 0x20) {
            char buf[8];
            std::snprintf(buf, sizeof buf, "\\u%04x", c);
            out += buf;
          } else {
            out += static_cast<char>(c);
          }
      }
    }
    out += '"';
  }

  void write(std::string& out) const {
    switch (type_) {
      case Type::Null: out += "null"; break;
      case Type::Bool: out += bool_ ? "true" : "false"; break;
      case Type::Int: out += std::to_string(int_); break;
      case Type::Num: {
        if (!std::isfinite(num_)) {
          out += "null";
        } else if (num_ == std::floor(num_) && std::fabs(num_) < 1e15) {
          out += std::to_string(static_cast<long long>(num_));
        } else {
          char buf[40];
          for (int precision = 1; precision <= 17; ++precision) {
            std::snprintf(buf, sizeof buf, "%.*g", precision, num_);
            if (std::strtod(buf, nullptr) == num_) break;
          }
          out += buf;
        }
        break;
      }
      case Type::Str: write_string(str_, out); break;
      case Type::Arr: {
        out += '[';
        for (std::size_t i = 0; i < arr_.size(); ++i) {
          if (i) out += ',';
          arr_[i].write(out);
        }
        out += ']';
        break;
      }
      case Type::Obj: {
        out += '{';
        for (std::size_t i = 0; i < obj_.size(); ++i) {
          if (i) out += ',';
          write_string(obj_[i].first, out);
          out += ':';
          obj_[i].second.write(out);
        }
        out += '}';
        break;
      }
    }
  }

  Type type_ = Type::Null;
  bool bool_ = false;
  long long int_ = 0;
  double num_ = 0;
  std::string str_;
  std::vector<Json> arr_;
  std::vector<Member> obj_;
};

namespace detail {

struct Parser {
  const std::string& s;
  std::size_t i = 0;

  [[noreturn]] void fail(const char* what) const {
    throw std::runtime_error(std::string("JSON: ") + what + " at offset " + std::to_string(i));
  }

  void ws() {
    while (i < s.size() && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) ++i;
  }

  char peek() const {
    if (i >= s.size()) fail("unexpected end of input");
    return s[i];
  }

  void expect(char c) {
    if (peek() != c) fail("unexpected character");
    ++i;
  }

  bool word(const char* text) {
    const std::string w(text);
    if (s.compare(i, w.size(), w) != 0) return false;
    i += w.size();
    return true;
  }

  unsigned hex4() {
    if (i + 4 > s.size()) fail("truncated escape");
    unsigned code = 0;
    for (int k = 0; k < 4; ++k) {
      const char c = s[i++];
      code <<= 4;
      if (c >= '0' && c <= '9') code |= static_cast<unsigned>(c - '0');
      else if (c >= 'a' && c <= 'f') code |= static_cast<unsigned>(c - 'a' + 10);
      else if (c >= 'A' && c <= 'F') code |= static_cast<unsigned>(c - 'A' + 10);
      else fail("bad escape");
    }
    return code;
  }

  static void utf8(std::string& out, unsigned cp) {
    if (cp < 0x80) {
      out += static_cast<char>(cp);
    } else if (cp < 0x800) {
      out += static_cast<char>(0xC0 | (cp >> 6));
      out += static_cast<char>(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
      out += static_cast<char>(0xE0 | (cp >> 12));
      out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
      out += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
      out += static_cast<char>(0xF0 | (cp >> 18));
      out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
      out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
      out += static_cast<char>(0x80 | (cp & 0x3F));
    }
  }

  std::string string() {
    expect('"');
    std::string out;
    for (;;) {
      const char c = peek();
      ++i;
      if (c == '"') return out;
      if (c != '\\') {
        out += c;
        continue;
      }
      const char e = peek();
      ++i;
      switch (e) {
        case 'n': out += '\n'; break;
        case 't': out += '\t'; break;
        case 'r': out += '\r'; break;
        case 'b': out += '\b'; break;
        case 'f': out += '\f'; break;
        case 'u': {
          unsigned code = hex4();
          if (code >= 0xD800 && code < 0xDC00 && s.compare(i, 2, "\\u") == 0) {
            i += 2;
            const unsigned low = hex4();
            code = 0x10000 + ((code - 0xD800) << 10) + ((low - 0xDC00) & 0x3FF);
          }
          utf8(out, code);
          break;
        }
        default: out += e;
      }
    }
  }

  Json value() {
    ws();
    const char c = peek();
    if (c == '{') {
      ++i;
      Json out = Json::object();
      ws();
      if (peek() == '}') {
        ++i;
        return out;
      }
      for (;;) {
        ws();
        std::string key = string();
        ws();
        expect(':');
        out.set(key, value());
        ws();
        if (peek() == ',') {
          ++i;
        } else {
          expect('}');
          return out;
        }
      }
    }
    if (c == '[') {
      ++i;
      Json out = Json::array();
      ws();
      if (peek() == ']') {
        ++i;
        return out;
      }
      for (;;) {
        out.push(value());
        ws();
        if (peek() == ',') {
          ++i;
        } else {
          expect(']');
          return out;
        }
      }
    }
    if (c == '"') return Json(string());
    if (word("true")) return Json(true);
    if (word("false")) return Json(false);
    if (word("null")) return Json();
    const std::size_t start = i;
    bool real = false;
    while (i < s.size() && (std::string("+-0123456789.eE").find(s[i]) != std::string::npos)) {
      if (s[i] == '.' || s[i] == 'e' || s[i] == 'E') real = true;
      ++i;
    }
    if (i == start) fail("unexpected character");
    const std::string number = s.substr(start, i - start);
    if (!real && number.size() < 19) return Json(std::strtoll(number.c_str(), nullptr, 10));
    return Json(std::strtod(number.c_str(), nullptr));
  }
};

}  // namespace detail

inline Json Json::parse(const std::string& text) {
  detail::Parser parser{text};
  Json out = parser.value();
  parser.ws();
  if (parser.i != text.size()) parser.fail("unexpected trailing characters");
  return out;
}

/// One element of a scene. Builder methods return the node so calls chain.
class Node {
 public:
  explicit Node(std::string type) : type_(std::move(type)) {}

  /// Set a property. Values may be any JSON-compatible data.
  Node& prop(const std::string& key, Json value) & {
    props_.set(key, std::move(value));
    return *this;
  }
  Node&& prop(const std::string& key, Json value) && { return std::move(prop(key, std::move(value))); }

  /// Give the node a stable identity (used for events, focus and AI targeting).
  Node& id(const std::string& value) & {
    id_ = value;
    return *this;
  }
  Node&& id(const std::string& value) && { return std::move(id(value)); }

  /// Bind a component event to a named action, optionally with a payload.
  Node& on(const std::string& event, const std::string& action) & {
    on_.set(event, Json::object({{"action", action}}));
    return *this;
  }
  Node&& on(const std::string& event, const std::string& action) && { return std::move(on(event, action)); }
  Node& on(const std::string& event, const std::string& action, Json payload) & {
    on_.set(event, Json::object({{"action", action}, {"payload", std::move(payload)}}));
    return *this;
  }
  Node&& on(const std::string& event, const std::string& action, Json payload) && {
    return std::move(on(event, action, std::move(payload)));
  }

  /// Attach an AI capability to this node, optionally with options.
  Node& ai(const std::string& capability, Json options = Json::object()) & {
    ai_.push(Json::object({{"capability", capability}, {"options", std::move(options)}}));
    return *this;
  }
  Node&& ai(const std::string& capability, Json options = Json::object()) && {
    return std::move(ai(capability, std::move(options)));
  }

  /// Append child nodes.
  Node& add(std::initializer_list<Node> nodes) & {
    children_.insert(children_.end(), nodes.begin(), nodes.end());
    return *this;
  }
  Node&& add(std::initializer_list<Node> nodes) && { return std::move(add(nodes)); }
  Node& add(const std::vector<Node>& nodes) & {
    children_.insert(children_.end(), nodes.begin(), nodes.end());
    return *this;
  }
  Node&& add(const std::vector<Node>& nodes) && { return std::move(add(nodes)); }
  Node& add(Node node) & {
    children_.push_back(std::move(node));
    return *this;
  }
  Node&& add(Node node) && { return std::move(add(std::move(node))); }

  Json to_json() const {
    Json out = Json::object({{"type", type_}, {"props", props_}});
    if (!id_.empty()) out.set("id", id_);
    if (!children_.empty()) {
      Json kids = Json::array();
      for (const Node& child : children_) kids.push(child.to_json());
      out.set("children", std::move(kids));
    }
    if (on_.size() > 0) out.set("on", on_);
    if (ai_.size() > 0) out.set("ai", ai_);
    return out;
  }

 private:
  std::string type_;
  std::string id_;
  Json props_ = Json::object();
  std::vector<Node> children_;
  Json on_ = Json::object();
  Json ai_ = Json::array();
};

inline Json::Json(const Node& node) { *this = node.to_json(); }

/// Thrown by Ctx::ai when a capability cannot be fulfilled.
class AIError : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

/// An interaction delivered to a handler.
struct Event {
  std::string name;
  std::string target;
  Json value;
  Json form;
  Json payload;
};

class App;

/// Per-session context: state, navigation, notifications and AI.
class Ctx {
 public:
  /// Session identifier.
  const std::string sid;
  /// Mutable per-session state (a JSON object; use get, set and has).
  Json& state;

  const std::string& route() const { return *route_; }
  const std::string& locale() const { return *locale_; }

  /// Show a transient notification. Tones: info, success, warning, danger.
  void toast(const std::string& text, const std::string& tone = "info");
  void navigate(const std::string& route);
  /// Invoke a capability and wait for its result. Throws AIError on failure.
  Json ai(const std::string& capability, Json input = Json::object());

 private:
  friend class App;
  Ctx(App& app, std::string session, Json& data, std::string* route, const std::string* locale)
      : sid(std::move(session)), state(data), app_(app), route_(route), locale_(locale) {}

  App& app_;
  std::string* route_;
  const std::string* locale_;
};

/// A Fluidian application.
class App {
 public:
  using View = std::function<Node(Ctx&)>;
  using Handler = std::function<void(Ctx&, const Event&)>;

  explicit App(std::string name) : name_(std::move(name)) {}

  /// Register the function that renders a session's scene.
  App& view(View fn) {
    view_ = std::move(fn);
    return *this;
  }

  /// Register a handler for a named action.
  App& on(const std::string& action, Handler fn) {
    handlers_[action] = std::move(fn);
    return *this;
  }

  /// Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in event.payload.
  App& action(const std::string& name, const std::string& description, Json params, Handler fn) {
    actions_.push(Json::object({{"name", name}, {"description", description}, {"params", std::move(params)}}));
    return on(name, std::move(fn));
  }

  /// Serve the wire protocol on stdin/stdout until the engine shuts the app down.
  void run() {
    send(Json::object({{"t", "ready"},
                       {"protocol", PROTOCOL},
                       {"sdk", "cpp"},
                       {"sdkVersion", VERSION},
                       {"app", Json::object({{"name", name_}, {"meta", Json::object()}})},
                       {"actions", actions_}}));
    for (;;) {
      Json message;
      if (!backlog_.empty()) {
        message = std::move(backlog_.front());
        backlog_.pop_front();
      } else if (!read(message)) {
        break;
      }
      if (!handle(message)) break;
    }
  }

 private:
  friend class Ctx;

  struct Session {
    Json state = Json::object();
    std::string route = "/";
    std::string locale = "en-US";
  };

  static std::string text(const Json& message, const char* key, const char* fallback) {
    const std::string value = message.get(key).as_string();
    return value.empty() ? std::string(fallback) : value;
  }

  void send(const Json& message) {
    std::string line = message.dump();
    line += '\n';
    std::fwrite(line.data(), 1, line.size(), stdout);
    std::fflush(stdout);
  }

  bool read(Json& out) {
    std::string line;
    while (std::getline(std::cin, line)) {
      if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
      try {
        Json message = Json::parse(line);
        if (message.is_object()) {
          out = std::move(message);
          return true;
        }
      } catch (const std::exception&) {
        // skip malformed lines
      }
    }
    return false;
  }

  Json invoke(const std::string& sid, const std::string& capability, Json input) {
    const std::string rid = "r" + std::to_string(++rid_);
    send(Json::object({{"t", "ai.invoke"}, {"rid", rid}, {"sid", sid}, {"capability", capability}, {"input", std::move(input)}}));
    for (;;) {
      Json message;
      if (!read(message)) throw AIError("engine disconnected");
      if (message.get("t").as_string() == "ai.result" && message.get("rid").as_string() == rid) {
        if (message.get("ok").as_bool()) return message.get("data");
        const Json& error = message.get("error");
        throw AIError(error.is_null() ? std::string("capability failed") : error.str());
      }
      backlog_.push_back(std::move(message));
    }
  }

  void render(const std::string& sid) {
    auto session = sessions_.find(sid);
    if (session == sessions_.end() || !view_) return;
    Ctx ctx(*this, sid, session->second.state, &session->second.route, &session->second.locale);
    send(Json::object({{"t", "scene"}, {"sid", sid}, {"root", view_(ctx).to_json()}}));
  }

  bool handle(const Json& message) {
    const std::string sid = message.get("sid").as_string();
    const std::string kind = message.get("t").as_string();
    if (kind == "open") {
      Session session;
      session.route = text(message, "route", "/");
      session.locale = text(message, "locale", "en-US");
      sessions_[sid] = std::move(session);
      render(sid);
    } else if (kind == "route") {
      auto session = sessions_.find(sid);
      if (session != sessions_.end()) {
        session->second.route = text(message, "route", "/");
        render(sid);
      }
    } else if (kind == "event") {
      const std::string action = message.get("name").as_string();
      auto session = sessions_.find(sid);
      auto handler = handlers_.find(action);
      if (session == sessions_.end()) {
        send(Json::object({{"t", "log"}, {"level", "warn"}, {"message", "event for unknown session " + sid}}));
      } else if (handler == handlers_.end()) {
        send(Json::object({{"t", "log"}, {"level", "warn"}, {"message", "no handler for action " + action}}));
      } else {
        Event event{action, message.get("target").as_string(), message.get("value"),
                    message.get("form").is_object() ? message.get("form") : Json::object(), message.get("payload")};
        Ctx ctx(*this, sid, session->second.state, &session->second.route, &session->second.locale);
        try {
          handler->second(ctx, event);
        } catch (const std::exception& error) {
          send(Json::object({{"t", "error"}, {"sid", sid}, {"message", std::string(error.what())}}));
          return true;
        } catch (...) {
          send(Json::object({{"t", "error"}, {"sid", sid}, {"message", "unknown error"}}));
          return true;
        }
        render(sid);
      }
    } else if (kind == "close") {
      sessions_.erase(sid);
    } else if (kind == "shutdown") {
      return false;
    }
    return true;
  }

  std::string name_;
  View view_;
  std::map<std::string, Handler> handlers_;
  Json actions_ = Json::array();
  std::map<std::string, Session> sessions_;
  std::deque<Json> backlog_;
  unsigned long rid_ = 0;
};

inline void Ctx::toast(const std::string& text, const std::string& tone) {
  app_.send(Json::object({{"t", "toast"}, {"sid", sid}, {"text", text}, {"tone", tone}}));
}

inline void Ctx::navigate(const std::string& route) {
  *route_ = route;
  app_.send(Json::object({{"t", "navigate"}, {"sid", sid}, {"route", route}}));
}

inline Json Ctx::ai(const std::string& capability, Json input) { return app_.invoke(sid, capability, std::move(input)); }

}  // namespace fluidian

#include "ui.hpp"
