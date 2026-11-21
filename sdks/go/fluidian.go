// Package fluidian is the Fluidian SDK for Go (standard library only).
//
//	app := fl.NewApp("Counter")
//	app.View(func(ctx *fl.Ctx) *fl.Node {
//		count, _ := ctx.State["count"].(int)
//		return fl.Page("Counter",
//			fl.Text(fmt.Sprintf("Count: %d", count)),
//			fl.Button("Add one").On("click", "increment"))
//	})
//	app.On("increment", func(ctx *fl.Ctx, ev fl.Event) {
//		count, _ := ctx.State["count"].(int)
//		ctx.State["count"] = count + 1
//	})
//	app.Run()
//
// Run it with `fluidian run -- go run .`.
package fluidian

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
)

// Version of the SDK.
const Version = "1.2.0"
const protocol = 1

// M is a JSON object and A a JSON array.
type (
	M = map[string]any
	A = []any
)

// Node is one element of a scene. Every method returns the node so calls can be chained.
type Node struct {
	typ      string
	id       string
	hasID    bool
	props    M
	children []*Node
	on       M
	ai       A
}

// NewNode creates a node of the given component type.
func NewNode(typ string) *Node { return &Node{typ: typ, props: M{}, on: M{}} }

// Prop sets a property. Values may be any JSON-compatible data.
func (n *Node) Prop(key string, value any) *Node { n.props[key] = value; return n }

// ID gives the node a stable identity (used for events, focus and AI targeting).
func (n *Node) ID(id string) *Node { n.id, n.hasID = id, true; return n }

// On binds a component event to a named action.
func (n *Node) On(event, action string) *Node { n.on[event] = M{"action": action}; return n }

// OnWith binds a component event to a named action with a payload.
func (n *Node) OnWith(event, action string, payload any) *Node {
	n.on[event] = M{"action": action, "payload": payload}
	return n
}

// AI attaches an AI capability to this node.
func (n *Node) AI(capability string) *Node { return n.AIWith(capability, M{}) }

// AIWith attaches an AI capability with options.
func (n *Node) AIWith(capability string, options M) *Node {
	if options == nil {
		options = M{}
	}
	n.ai = append(n.ai, M{"capability": capability, "options": options})
	return n
}

// Add appends child nodes; nil entries are skipped.
func (n *Node) Add(children ...*Node) *Node {
	for _, c := range children {
		if c != nil {
			n.children = append(n.children, c)
		}
	}
	return n
}

// JSON returns the wire representation of the node.
func (n *Node) JSON() M {
	out := M{"type": n.typ, "props": n.props}
	if n.hasID {
		out["id"] = n.id
	}
	if len(n.children) > 0 {
		kids := make(A, len(n.children))
		for i, c := range n.children {
			kids[i] = c.JSON()
		}
		out["children"] = kids
	}
	if len(n.on) > 0 {
		out["on"] = n.on
	}
	if len(n.ai) > 0 {
		out["ai"] = n.ai
	}
	return out
}

// Event is an interaction delivered to a handler.
type Event struct {
	Name    string
	Target  string
	Value   any
	Form    M
	Payload any
}

type session struct {
	state  M
	route  string
	locale string
}

// Ctx is the per-session context: state, navigation, notifications and AI.
type Ctx struct {
	app     *App
	session *session
	SID     string
	State   M
}

// Route returns the session's current route.
func (c *Ctx) Route() string { return c.session.route }

// Locale returns the session's locale.
func (c *Ctx) Locale() string { return c.session.locale }

// Toast shows a transient message; tone is info, success, warning or danger.
func (c *Ctx) Toast(text, tone string) {
	c.app.send(M{"t": "toast", "sid": c.SID, "text": text, "tone": tone})
}

// Navigate moves the session to another route.
func (c *Ctx) Navigate(route string) {
	c.session.route = route
	c.app.send(M{"t": "navigate", "sid": c.SID, "route": route})
}

// AI invokes a capability and waits for its result.
func (c *Ctx) AI(capability string, input M) (M, error) {
	if input == nil {
		input = M{}
	}
	return c.app.invoke(c.SID, capability, input)
}

// Handler reacts to an action.
type Handler func(ctx *Ctx, ev Event)

// App is a Fluidian application.
type App struct {
	Name     string
	Meta     M
	view     func(ctx *Ctx) *Node
	handlers map[string]Handler
	actions  A
	sessions map[string]*session
	backlog  []M
	rid      int
	in       *bufio.Reader
	out      *bufio.Writer
}

// NewApp creates an application.
func NewApp(name string) *App {
	return &App{Name: name, Meta: M{}, handlers: map[string]Handler{}, actions: A{}, sessions: map[string]*session{},
		in: bufio.NewReaderSize(os.Stdin, 1<<16), out: bufio.NewWriterSize(os.Stdout, 1<<16)}
}

// View registers the function that renders a session's scene.
func (a *App) View(fn func(ctx *Ctx) *Node) *App { a.view = fn; return a }

// On registers a handler for a named action.
func (a *App) On(action string, fn Handler) *App { a.handlers[action] = fn; return a }

// Action registers a handler that the Intent Bar and Copilot may invoke; arguments arrive in ev.Payload.
func (a *App) Action(name, description string, params M, fn Handler) *App {
	if params == nil {
		params = M{}
	}
	a.actions = append(a.actions, M{"name": name, "description": description, "params": params})
	return a.On(name, fn)
}

func (a *App) send(msg M) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(msg); err != nil {
		fmt.Fprintln(os.Stderr, "fluidian: cannot encode message:", err)
		return
	}
	a.out.Write(buf.Bytes())
	a.out.Flush()
}

func (a *App) read() M {
	for {
		line, err := a.in.ReadBytes('\n')
		if len(bytes.TrimSpace(line)) > 0 {
			var msg M
			if json.Unmarshal(line, &msg) == nil && msg != nil {
				return msg
			}
		}
		if err != nil {
			if !errors.Is(err, io.EOF) {
				fmt.Fprintln(os.Stderr, "fluidian: read error:", err)
			}
			return nil
		}
	}
}

func (a *App) invoke(sid, capability string, input M) (M, error) {
	a.rid++
	rid := fmt.Sprintf("r%d", a.rid)
	a.send(M{"t": "ai.invoke", "rid": rid, "sid": sid, "capability": capability, "input": input})
	for {
		msg := a.read()
		if msg == nil {
			return nil, errors.New("engine disconnected")
		}
		if msg["t"] == "ai.result" && msg["rid"] == rid {
			if ok, _ := msg["ok"].(bool); ok {
				data, _ := msg["data"].(M)
				if data == nil {
					data = M{}
				}
				return data, nil
			}
			reason, _ := msg["error"].(string)
			if reason == "" {
				reason = "capability failed"
			}
			return nil, errors.New(reason)
		}
		a.backlog = append(a.backlog, msg)
	}
}

func str(v any, fallback string) string {
	if s, ok := v.(string); ok && s != "" {
		return s
	}
	return fallback
}

func (a *App) render(sid string) {
	s, ok := a.sessions[sid]
	if !ok || a.view == nil {
		return
	}
	root := a.view(&Ctx{app: a, session: s, SID: sid, State: s.state})
	a.send(M{"t": "scene", "sid": sid, "root": root.JSON()})
}

func (a *App) dispatch(sid string, s *session, handler Handler, msg M) (failed bool) {
	defer func() {
		if r := recover(); r != nil {
			a.send(M{"t": "error", "sid": sid, "message": fmt.Sprint(r)})
			failed = true
		}
	}()
	form, _ := msg["form"].(M)
	if form == nil {
		form = M{}
	}
	handler(&Ctx{app: a, session: s, SID: sid, State: s.state},
		Event{Name: str(msg["name"], ""), Target: str(msg["target"], ""), Value: msg["value"], Form: form, Payload: msg["payload"]})
	return false
}

func (a *App) handle(msg M) bool {
	sid := str(msg["sid"], "")
	switch msg["t"] {
	case "open":
		a.sessions[sid] = &session{state: M{}, route: str(msg["route"], "/"), locale: str(msg["locale"], "en-US")}
		a.render(sid)
	case "route":
		if s, ok := a.sessions[sid]; ok {
			s.route = str(msg["route"], "/")
			a.render(sid)
		}
	case "event":
		name := str(msg["name"], "")
		s, known := a.sessions[sid]
		handler, bound := a.handlers[name]
		switch {
		case !known:
			a.send(M{"t": "log", "level": "warn", "message": "event for unknown session " + sid})
		case !bound:
			a.send(M{"t": "log", "level": "warn", "message": "no handler for action " + name})
		default:
			if !a.dispatch(sid, s, handler, msg) {
				a.render(sid)
			}
		}
	case "close":
		delete(a.sessions, sid)
	case "shutdown":
		return false
	}
	return true
}

// Run serves the wire protocol on stdin/stdout until the engine shuts the app down.
func (a *App) Run() {
	a.send(M{"t": "ready", "protocol": protocol, "sdk": "go", "sdkVersion": Version, "app": M{"name": a.Name, "meta": a.Meta}, "actions": a.actions})
	for {
		var msg M
		if len(a.backlog) > 0 {
			msg, a.backlog = a.backlog[0], a.backlog[1:]
		} else {
			msg = a.read()
		}
		if msg == nil || !a.handle(msg) {
			return
		}
	}
}
