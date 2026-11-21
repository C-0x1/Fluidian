//! Fluidian SDK for Rust.
//!
//! A Fluidian app describes its interface as a tree of [`Node`]s and reacts to
//! named actions. The engine renders the tree in the browser, runs every AI
//! capability, and talks to this process over a line-delimited JSON protocol.
//! The crate has no dependencies.
//!
//! ```no_run
//! use fluidian::{ui, App};
//!
//! fn main() {
//!     let mut app = App::new("Counter");
//!     app.view(|ctx| {
//!         ui::page("Counter", vec![
//!             ui::text(&format!("Count: {}", ctx.state.int("count"))),
//!             ui::button("Add one").on("click", "increment"),
//!         ])
//!     });
//!     app.on("increment", |ctx, _| {
//!         let next = ctx.state.int("count") + 1;
//!         ctx.state.set("count", next);
//!         Ok(())
//!     });
//!     app.run();
//! }
//! ```
//!
//! Run it with `fluidian run -- cargo run --quiet`.

use std::collections::{BTreeMap, VecDeque};
use std::fmt;
use std::io::{self, BufRead, Write};

pub mod ui;

/// SDK version.
pub const VERSION: &str = "1.2.0";
const PROTOCOL: i64 = 1;

/// Error type returned by handlers.
pub type Error = Box<dyn std::error::Error + Send + Sync>;
/// Result type returned by handlers.
pub type Result<T = ()> = std::result::Result<T, Error>;

// ---------------------------------------------------------------- JSON

/// A JSON value. Objects keep their insertion order.
#[derive(Clone, Debug, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Int(i64),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

static NULL: Json = Json::Null;

impl Json {
    /// Member of an object, or `Json::Null` when absent.
    pub fn get(&self, key: &str) -> &Json {
        if let Json::Obj(pairs) = self {
            for (k, v) in pairs {
                if k == key {
                    return v;
                }
            }
        }
        &NULL
    }

    /// Element of an array, or `Json::Null` when out of range.
    pub fn at(&self, index: usize) -> &Json {
        match self {
            Json::Arr(items) => items.get(index).unwrap_or(&NULL),
            _ => &NULL,
        }
    }

    /// Insert or replace a member. Turns non-objects into an object.
    pub fn set(&mut self, key: &str, value: impl Into<Json>) {
        if !matches!(self, Json::Obj(_)) {
            *self = Json::Obj(Vec::new());
        }
        if let Json::Obj(pairs) = self {
            let value = value.into();
            match pairs.iter_mut().find(|(k, _)| k == key) {
                Some(pair) => pair.1 = value,
                None => pairs.push((key.to_string(), value)),
            }
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Json::Null)
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Json::Str(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_i64(&self) -> Option<i64> {
        match self {
            Json::Int(n) => Some(*n),
            Json::Num(n) if n.fract() == 0.0 => Some(*n as i64),
            _ => None,
        }
    }

    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Json::Int(n) => Some(*n as f64),
            Json::Num(n) => Some(*n),
            _ => None,
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(b) => Some(*b),
            _ => None,
        }
    }

    /// Elements of an array (empty for anything else).
    pub fn items(&self) -> &[Json] {
        match self {
            Json::Arr(items) => items,
            _ => &[],
        }
    }

    /// Serialise to compact JSON text.
    pub fn encode(&self) -> String {
        let mut out = String::with_capacity(128);
        self.write(&mut out);
        out
    }

    fn write(&self, out: &mut String) {
        match self {
            Json::Null => out.push_str("null"),
            Json::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
            Json::Int(n) => out.push_str(&n.to_string()),
            Json::Num(n) => {
                if !n.is_finite() {
                    out.push_str("null");
                } else if n.fract() == 0.0 && n.abs() < 1e15 {
                    out.push_str(&(*n as i64).to_string());
                } else {
                    out.push_str(&n.to_string());
                }
            }
            Json::Str(s) => write_string(s, out),
            Json::Arr(items) => {
                out.push('[');
                for (i, item) in items.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    item.write(out);
                }
                out.push(']');
            }
            Json::Obj(pairs) => {
                out.push('{');
                for (i, (k, v)) in pairs.iter().enumerate() {
                    if i > 0 {
                        out.push(',');
                    }
                    write_string(k, out);
                    out.push(':');
                    v.write(out);
                }
                out.push('}');
            }
        }
    }

    /// Parse JSON text.
    pub fn parse(text: &str) -> std::result::Result<Json, String> {
        let mut parser = Parser { s: text.as_bytes(), i: 0 };
        let value = parser.value()?;
        parser.ws();
        if parser.i != parser.s.len() {
            return Err(format!("unexpected trailing characters at {}", parser.i));
        }
        Ok(value)
    }
}

fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

/// Strings print without quotes; everything else prints as JSON.
impl fmt::Display for Json {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Json::Str(s) => f.write_str(s),
            other => f.write_str(&other.encode()),
        }
    }
}

struct Parser<'a> {
    s: &'a [u8],
    i: usize,
}

impl<'a> Parser<'a> {
    fn ws(&mut self) {
        while self.i < self.s.len() && matches!(self.s[self.i], b' ' | b'\t' | b'\n' | b'\r') {
            self.i += 1;
        }
    }

    fn peek(&self) -> std::result::Result<u8, String> {
        self.s.get(self.i).copied().ok_or_else(|| "unexpected end of input".to_string())
    }

    fn expect(&mut self, c: u8) -> std::result::Result<(), String> {
        if self.peek()? != c {
            return Err(format!("expected '{}' at {}", c as char, self.i));
        }
        self.i += 1;
        Ok(())
    }

    fn literal(&mut self, word: &str, value: Json) -> std::result::Result<Json, String> {
        if self.s[self.i..].starts_with(word.as_bytes()) {
            self.i += word.len();
            Ok(value)
        } else {
            Err(format!("unexpected token at {}", self.i))
        }
    }

    fn value(&mut self) -> std::result::Result<Json, String> {
        self.ws();
        match self.peek()? {
            b'{' => {
                self.i += 1;
                let mut pairs = Vec::new();
                self.ws();
                if self.peek()? == b'}' {
                    self.i += 1;
                    return Ok(Json::Obj(pairs));
                }
                loop {
                    self.ws();
                    let key = self.string()?;
                    self.ws();
                    self.expect(b':')?;
                    let value = self.value()?;
                    pairs.push((key, value));
                    self.ws();
                    if self.peek()? == b',' {
                        self.i += 1;
                    } else {
                        self.expect(b'}')?;
                        return Ok(Json::Obj(pairs));
                    }
                }
            }
            b'[' => {
                self.i += 1;
                let mut items = Vec::new();
                self.ws();
                if self.peek()? == b']' {
                    self.i += 1;
                    return Ok(Json::Arr(items));
                }
                loop {
                    items.push(self.value()?);
                    self.ws();
                    if self.peek()? == b',' {
                        self.i += 1;
                    } else {
                        self.expect(b']')?;
                        return Ok(Json::Arr(items));
                    }
                }
            }
            b'"' => Ok(Json::Str(self.string()?)),
            b't' => self.literal("true", Json::Bool(true)),
            b'f' => self.literal("false", Json::Bool(false)),
            b'n' => self.literal("null", Json::Null),
            _ => {
                let start = self.i;
                let mut real = false;
                while self.i < self.s.len() && matches!(self.s[self.i], b'0'..=b'9' | b'+' | b'-' | b'.' | b'e' | b'E') {
                    real |= matches!(self.s[self.i], b'.' | b'e' | b'E');
                    self.i += 1;
                }
                let text = std::str::from_utf8(&self.s[start..self.i]).unwrap_or("");
                if text.is_empty() {
                    return Err(format!("unexpected character at {}", self.i));
                }
                if !real {
                    if let Ok(n) = text.parse::<i64>() {
                        return Ok(Json::Int(n));
                    }
                }
                text.parse::<f64>().map(Json::Num).map_err(|_| format!("bad number at {}", start))
            }
        }
    }

    fn hex4(&mut self) -> std::result::Result<u32, String> {
        let chunk = self.s.get(self.i..self.i + 4).ok_or("truncated escape")?;
        let text = std::str::from_utf8(chunk).map_err(|_| "bad escape")?;
        let code = u32::from_str_radix(text, 16).map_err(|_| "bad escape")?;
        self.i += 4;
        Ok(code)
    }

    fn string(&mut self) -> std::result::Result<String, String> {
        self.expect(b'"')?;
        let mut buf: Vec<u8> = Vec::new();
        loop {
            let c = self.peek()?;
            self.i += 1;
            match c {
                b'"' => break,
                b'\\' => {
                    let e = self.peek()?;
                    self.i += 1;
                    match e {
                        b'n' => buf.push(b'\n'),
                        b't' => buf.push(b'\t'),
                        b'r' => buf.push(b'\r'),
                        b'b' => buf.push(8),
                        b'f' => buf.push(12),
                        b'u' => {
                            let mut code = self.hex4()?;
                            if (0xD800..0xDC00).contains(&code) && self.s[self.i..].starts_with(b"\\u") {
                                self.i += 2;
                                let low = self.hex4()?;
                                code = 0x10000 + ((code - 0xD800) << 10) + (low.wrapping_sub(0xDC00) & 0x3FF);
                            }
                            let ch = char::from_u32(code).unwrap_or('\u{FFFD}');
                            let mut tmp = [0u8; 4];
                            buf.extend_from_slice(ch.encode_utf8(&mut tmp).as_bytes());
                        }
                        other => buf.push(other),
                    }
                }
                other => buf.push(other),
            }
        }
        Ok(String::from_utf8_lossy(&buf).into_owned())
    }
}

impl From<bool> for Json {
    fn from(v: bool) -> Json {
        Json::Bool(v)
    }
}

macro_rules! json_from_int {
    ($($t:ty),*) => {$(
        impl From<$t> for Json {
            fn from(v: $t) -> Json {
                Json::Int(v as i64)
            }
        }
    )*};
}
json_from_int!(i8, i16, i32, i64, isize, u8, u16, u32, u64, usize);

impl From<f32> for Json {
    fn from(v: f32) -> Json {
        Json::Num(v as f64)
    }
}

impl From<f64> for Json {
    fn from(v: f64) -> Json {
        Json::Num(v)
    }
}

impl From<&str> for Json {
    fn from(v: &str) -> Json {
        Json::Str(v.to_string())
    }
}

impl From<String> for Json {
    fn from(v: String) -> Json {
        Json::Str(v)
    }
}

impl From<&String> for Json {
    fn from(v: &String) -> Json {
        Json::Str(v.clone())
    }
}

impl From<&Json> for Json {
    fn from(v: &Json) -> Json {
        v.clone()
    }
}

impl<T: Into<Json>> From<Vec<T>> for Json {
    fn from(v: Vec<T>) -> Json {
        Json::Arr(v.into_iter().map(Into::into).collect())
    }
}

impl<T: Into<Json>> From<Option<T>> for Json {
    fn from(v: Option<T>) -> Json {
        v.map(Into::into).unwrap_or(Json::Null)
    }
}

impl From<Node> for Json {
    fn from(v: Node) -> Json {
        v.to_json()
    }
}

/// Build a JSON object: `jobj!{"label" => "Save", "count" => 3}`.
#[macro_export]
macro_rules! jobj {
    () => { $crate::Json::Obj(::std::vec::Vec::new()) };
    ($($key:expr => $value:expr),+ $(,)?) => {
        $crate::Json::Obj(::std::vec![$((::std::string::String::from($key), $crate::Json::from($value))),+])
    };
}

/// Build a JSON array: `jarr!["a", 2, true]`.
#[macro_export]
macro_rules! jarr {
    () => { $crate::Json::Arr(::std::vec::Vec::new()) };
    ($($value:expr),+ $(,)?) => {
        $crate::Json::Arr(::std::vec![$($crate::Json::from($value)),+])
    };
}

// ---------------------------------------------------------------- scene

/// One element of a scene. Builder methods consume and return the node so calls chain.
#[derive(Clone, Debug)]
pub struct Node {
    kind: String,
    id: Option<String>,
    props: Vec<(String, Json)>,
    children: Vec<Node>,
    on: Vec<(String, Json)>,
    ai: Vec<Json>,
}

impl Node {
    pub fn new(kind: &str) -> Node {
        Node { kind: kind.to_string(), id: None, props: Vec::new(), children: Vec::new(), on: Vec::new(), ai: Vec::new() }
    }

    /// Set a property. Values may be any JSON-compatible data.
    pub fn prop(mut self, key: &str, value: impl Into<Json>) -> Node {
        let value = value.into();
        match self.props.iter_mut().find(|(k, _)| k == key) {
            Some(pair) => pair.1 = value,
            None => self.props.push((key.to_string(), value)),
        }
        self
    }

    /// Give the node a stable identity (used for events, focus and AI targeting).
    pub fn id(mut self, id: &str) -> Node {
        self.id = Some(id.to_string());
        self
    }

    /// Bind a component event to a named action.
    pub fn on(mut self, event: &str, action: &str) -> Node {
        self.on.push((event.to_string(), jobj! {"action" => action}));
        self
    }

    /// Bind a component event to a named action with a payload.
    pub fn on_with(mut self, event: &str, action: &str, payload: impl Into<Json>) -> Node {
        self.on.push((event.to_string(), jobj! {"action" => action, "payload" => payload.into()}));
        self
    }

    /// Attach an AI capability to this node.
    pub fn ai(self, capability: &str) -> Node {
        self.ai_with(capability, jobj! {})
    }

    /// Attach an AI capability with options.
    pub fn ai_with(mut self, capability: &str, options: impl Into<Json>) -> Node {
        self.ai.push(jobj! {"capability" => capability, "options" => options.into()});
        self
    }

    /// Append child nodes.
    pub fn add(mut self, children: Vec<Node>) -> Node {
        self.children.extend(children);
        self
    }

    /// Append one child node.
    pub fn push(mut self, child: Node) -> Node {
        self.children.push(child);
        self
    }

    pub fn to_json(&self) -> Json {
        let mut pairs = vec![
            ("type".to_string(), Json::Str(self.kind.clone())),
            ("props".to_string(), Json::Obj(self.props.clone())),
        ];
        if let Some(id) = &self.id {
            pairs.push(("id".to_string(), Json::Str(id.clone())));
        }
        if !self.children.is_empty() {
            pairs.push(("children".to_string(), Json::Arr(self.children.iter().map(Node::to_json).collect())));
        }
        if !self.on.is_empty() {
            pairs.push(("on".to_string(), Json::Obj(self.on.clone())));
        }
        if !self.ai.is_empty() {
            pairs.push(("ai".to_string(), Json::Arr(self.ai.clone())));
        }
        Json::Obj(pairs)
    }
}

// ---------------------------------------------------------------- app

/// Mutable per-session state.
#[derive(Clone, Debug, Default)]
pub struct State(BTreeMap<String, Json>);

impl State {
    pub fn get(&self, key: &str) -> &Json {
        self.0.get(key).unwrap_or(&NULL)
    }

    pub fn has(&self, key: &str) -> bool {
        self.0.contains_key(key)
    }

    pub fn set(&mut self, key: &str, value: impl Into<Json>) {
        self.0.insert(key.to_string(), value.into());
    }

    pub fn remove(&mut self, key: &str) {
        self.0.remove(key);
    }

    /// Integer value, or 0 when absent.
    pub fn int(&self, key: &str) -> i64 {
        self.get(key).as_i64().unwrap_or(0)
    }

    /// Text value, or the fallback when absent.
    pub fn text(&self, key: &str, fallback: &str) -> String {
        match self.get(key) {
            Json::Null => fallback.to_string(),
            other => other.to_string(),
        }
    }
}

/// An interaction delivered to a handler.
#[derive(Clone, Debug)]
pub struct Event {
    pub name: String,
    pub target: Option<String>,
    pub value: Json,
    pub form: Json,
    pub payload: Json,
}

/// Returned by [`Ctx::ai`] when a capability cannot be fulfilled.
#[derive(Clone, Debug)]
pub struct AiError(pub String);

impl fmt::Display for AiError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for AiError {}

struct Session {
    state: State,
    route: String,
    locale: String,
}

struct Io {
    backlog: VecDeque<Json>,
    rid: u64,
}

impl Io {
    fn send(&mut self, message: &Json) {
        let stdout = io::stdout();
        let mut out = stdout.lock();
        let _ = out.write_all(message.encode().as_bytes());
        let _ = out.write_all(b"\n");
        let _ = out.flush();
    }

    fn read(&mut self) -> Option<Json> {
        let stdin = io::stdin();
        loop {
            let mut line = Vec::new();
            match stdin.lock().read_until(b'\n', &mut line) {
                Ok(0) | Err(_) => return None,
                Ok(_) => {}
            }
            let text = String::from_utf8_lossy(&line);
            let text = text.trim();
            if text.is_empty() {
                continue;
            }
            if let Ok(message @ Json::Obj(_)) = Json::parse(text) {
                return Some(message);
            }
        }
    }
}

/// Per-session context: state, navigation, notifications and AI.
pub struct Ctx<'a> {
    /// Session identifier.
    pub sid: &'a str,
    /// Mutable per-session state.
    pub state: &'a mut State,
    route: &'a mut String,
    locale: &'a str,
    io: &'a mut Io,
}

impl<'a> Ctx<'a> {
    pub fn route(&self) -> &str {
        self.route
    }

    pub fn locale(&self) -> &str {
        self.locale
    }

    /// Show a transient notification. Tones: info, success, warning, danger.
    pub fn toast(&mut self, text: &str, tone: &str) {
        self.io.send(&jobj! {"t" => "toast", "sid" => self.sid, "text" => text, "tone" => tone});
    }

    pub fn navigate(&mut self, route: &str) {
        *self.route = route.to_string();
        self.io.send(&jobj! {"t" => "navigate", "sid" => self.sid, "route" => route});
    }

    /// Invoke a capability and wait for its result.
    pub fn ai(&mut self, capability: &str, input: impl Into<Json>) -> std::result::Result<Json, AiError> {
        self.io.rid += 1;
        let rid = format!("r{}", self.io.rid);
        self.io.send(&jobj! {
            "t" => "ai.invoke", "rid" => rid.as_str(), "sid" => self.sid,
            "capability" => capability, "input" => input.into()
        });
        loop {
            let message = match self.io.read() {
                Some(message) => message,
                None => return Err(AiError("engine disconnected".to_string())),
            };
            if message.get("t").as_str() == Some("ai.result") && message.get("rid").as_str() == Some(rid.as_str()) {
                if message.get("ok").as_bool() == Some(true) {
                    return Ok(message.get("data").clone());
                }
                let error = message.get("error");
                return Err(AiError(if error.is_null() { "capability failed".to_string() } else { error.to_string() }));
            }
            self.io.backlog.push_back(message);
        }
    }
}

type View = Box<dyn Fn(&Ctx) -> Node>;
type Handler = Box<dyn FnMut(&mut Ctx, &Event) -> Result>;

/// A Fluidian application.
pub struct App {
    name: String,
    view: Option<View>,
    handlers: BTreeMap<String, Handler>,
    actions: Vec<Json>,
    sessions: BTreeMap<String, Session>,
    io: Io,
}

impl App {
    pub fn new(name: &str) -> App {
        App {
            name: name.to_string(),
            view: None,
            handlers: BTreeMap::new(),
            actions: Vec::new(),
            sessions: BTreeMap::new(),
            io: Io { backlog: VecDeque::new(), rid: 0 },
        }
    }

    /// Register the function that renders a session's scene.
    pub fn view(&mut self, view: impl Fn(&Ctx) -> Node + 'static) -> &mut App {
        self.view = Some(Box::new(view));
        self
    }

    /// Register a handler for a named action.
    pub fn on(&mut self, action: &str, handler: impl FnMut(&mut Ctx, &Event) -> Result + 'static) -> &mut App {
        self.handlers.insert(action.to_string(), Box::new(handler));
        self
    }

    /// Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`.
    pub fn action(
        &mut self,
        name: &str,
        description: &str,
        params: Json,
        handler: impl FnMut(&mut Ctx, &Event) -> Result + 'static,
    ) -> &mut App {
        self.actions.push(jobj! {"name" => name, "description" => description, "params" => params});
        self.on(name, handler)
    }

    fn render(&mut self, sid: &str) {
        let view = match &self.view {
            Some(view) => view,
            None => return,
        };
        let session = match self.sessions.get_mut(sid) {
            Some(session) => session,
            None => return,
        };
        let root = {
            let ctx = Ctx { sid, state: &mut session.state, route: &mut session.route, locale: &session.locale, io: &mut self.io };
            view(&ctx).to_json()
        };
        self.io.send(&jobj! {"t" => "scene", "sid" => sid, "root" => root});
    }

    fn handle(&mut self, message: Json) -> bool {
        let sid = message.get("sid").as_str().unwrap_or("").to_string();
        let text = |key: &str, fallback: &str| -> String {
            match message.get(key).as_str() {
                Some(s) if !s.is_empty() => s.to_string(),
                _ => fallback.to_string(),
            }
        };
        match message.get("t").as_str().unwrap_or("") {
            "open" => {
                let session = Session { state: State::default(), route: text("route", "/"), locale: text("locale", "en-US") };
                self.sessions.insert(sid.clone(), session);
                self.render(&sid);
            }
            "route" => {
                if let Some(session) = self.sessions.get_mut(&sid) {
                    session.route = text("route", "/");
                    self.render(&sid);
                }
            }
            "event" => {
                let action = text("name", "");
                let session = match self.sessions.get_mut(&sid) {
                    Some(session) => session,
                    None => {
                        self.io.send(&jobj! {"t" => "log", "level" => "warn", "message" => format!("event for unknown session {}", sid)});
                        return true;
                    }
                };
                let handler = match self.handlers.get_mut(&action) {
                    Some(handler) => handler,
                    None => {
                        self.io.send(&jobj! {"t" => "log", "level" => "warn", "message" => format!("no handler for action {}", action)});
                        return true;
                    }
                };
                let event = Event {
                    name: action.clone(),
                    target: message.get("target").as_str().map(str::to_string),
                    value: message.get("value").clone(),
                    form: match message.get("form") {
                        form @ Json::Obj(_) => form.clone(),
                        _ => jobj! {},
                    },
                    payload: message.get("payload").clone(),
                };
                let outcome = {
                    let mut ctx = Ctx { sid: &sid, state: &mut session.state, route: &mut session.route, locale: &session.locale, io: &mut self.io };
                    handler(&mut ctx, &event)
                };
                if let Err(error) = outcome {
                    self.io.send(&jobj! {"t" => "error", "sid" => sid.as_str(), "message" => error.to_string()});
                    return true;
                }
                self.render(&sid);
            }
            "close" => {
                self.sessions.remove(&sid);
            }
            "shutdown" => return false,
            _ => {}
        }
        true
    }

    /// Serve the wire protocol on stdin/stdout until the engine shuts the app down.
    pub fn run(&mut self) {
        let ready = jobj! {
            "t" => "ready", "protocol" => PROTOCOL, "sdk" => "rust", "sdkVersion" => VERSION,
            "app" => jobj!{"name" => self.name.as_str(), "meta" => jobj!{}},
            "actions" => Json::Arr(self.actions.clone())
        };
        self.io.send(&ready);
        loop {
            let message = match self.io.backlog.pop_front() {
                Some(message) => message,
                None => match self.io.read() {
                    Some(message) => message,
                    None => break,
                },
            };
            if !self.handle(message) {
                break;
            }
        }
    }
}
