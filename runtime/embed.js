/* <fluidian-app>: embed a Fluidian application in any page.
 *
 *   <script src="https://app.example.com/_fluidian/embed.js"></script>
 *   <fluidian-app src="https://app.example.com" route="/pricing" theme="ocean"></fluidian-app>
 *
 * Works wherever custom elements do: plain HTML, React, Vue, Svelte, Angular,
 * Rails or Django templates. The application runs in a sandboxed frame served
 * by its own engine, so its styles and scripts cannot collide with the host
 * page. The element sizes itself to the content unless a height is given, and
 * re-dispatches what happens inside as DOM events:
 *
 *   fluidian:ready     { route }
 *   fluidian:navigate  { route }
 *   fluidian:resize    { height }
 *
 * The engine must allow the host origin: set FLUIDIAN_EMBED_ORIGINS, for
 * example FLUIDIAN_EMBED_ORIGINS=https://www.example.com.
 */
(function () {
  if (typeof customElements === "undefined" || customElements.get("fluidian-app")) return;
  var script = document.currentScript;
  var home = script && script.src ? new URL(script.src).origin : location.origin;

  class FluidianApp extends HTMLElement {
    static get observedAttributes() { return ["src", "route", "theme", "platform", "density", "height"]; }

    constructor() {
      super();
      this._frame = null;
      this._onMessage = this._onMessage.bind(this);
    }

    connectedCallback() {
      if (!this._frame) {
        var root = this.attachShadow({ mode: "open" });
        var style = document.createElement("style");
        style.textContent = ":host{display:block;inline-size:100%}iframe{display:block;inline-size:100%;border:0;background:transparent;color-scheme:light dark}";
        this._frame = document.createElement("iframe");
        this._frame.setAttribute("title", this.getAttribute("title") || "Fluidian application");
        this._frame.setAttribute("loading", this.getAttribute("loading") || "lazy");
        this._frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups allow-downloads");
        this._frame.setAttribute("allow", "clipboard-write; microphone");
        root.append(style, this._frame);
      }
      window.addEventListener("message", this._onMessage);
      this._load();
    }

    disconnectedCallback() { window.removeEventListener("message", this._onMessage); }

    attributeChangedCallback(name, before, after) {
      if (!this._frame || before === after) return;
      if (name === "height") this._size(); else this._load();
    }

    get origin() { return new URL(this.getAttribute("src") || home, location.href).origin; }

    /** The address the frame shows: the engine's origin, the route, and the presentation options. */
    get url() {
      var url = new URL(this.getAttribute("route") || "/", new URL(this.getAttribute("src") || home, location.href));
      var self = this;
      ["theme", "platform", "density"].forEach(function (key) { if (self.getAttribute(key)) url.searchParams.set(key, self.getAttribute(key)); });
      url.searchParams.set("embed", "1");
      return url.href;
    }

    navigate(route) { this.setAttribute("route", route); }

    _load() { if (this._frame.src !== this.url) this._frame.src = this.url; this._size(); }

    _size(measured) {
      var fixed = this.getAttribute("height");
      if (fixed) this._frame.style.blockSize = /^\d+$/.test(fixed) ? fixed + "px" : fixed;
      else if (measured) this._frame.style.blockSize = Math.max(120, Math.ceil(measured)) + "px";
      else if (!this._frame.style.blockSize) this._frame.style.blockSize = "480px";
    }

    _onMessage(event) {
      var data = event.data;
      if (!this._frame || event.source !== this._frame.contentWindow || event.origin !== this.origin || !data || data.source !== "fluidian") return;
      if (data.type === "resize") this._size(data.height);
      if (data.type === "ready" || data.type === "navigate" || data.type === "resize") {
        this.dispatchEvent(new CustomEvent("fluidian:" + data.type, { detail: data, bubbles: true, composed: true }));
      }
    }
  }

  customElements.define("fluidian-app", FluidianApp);
})();
