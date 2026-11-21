<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Getting started

This guide takes you from a fresh Ubuntu machine to a running showcase, a passing test suite and your own app. Every command can be copied as it is.

## The short version

From the unzipped `fluidian` folder, three commands do everything:

```bash
bash scripts/setup-ubuntu.sh     # installs Python, Node.js, the other language toolchains and a browser, then checks them
bash scripts/set-api-key.sh      # optional: stores your OpenAI key; skip it to use the offline engine
bash scripts/test-all.sh         # runs every test and ends with RESULT: ALL TESTS PASSED
```

Then:

```bash
./fluidian showcase --open       # 85 complete screens
./fluidian gallery --open        # every AI capability family, live
```

The rest of this page explains each step and what to do when something differs.

## 1. Requirements

| Needed for | Requirement |
| --- | --- |
| The framework | Python 3.9 or newer. Ubuntu 22.04 and 24.04 include it. |
| Runtime tests, static export | Node.js 18 or newer (optional) |
| SDK tests | The toolchain of each language you care about (optional) |
| Browser tests, screenshots | Chrome or Chromium (optional) |
| Model-backed answers | An OpenAI API key (optional) |

Nothing has to be installed with `pip` or `npm`. The engine uses the Python standard library only, and the browser runtime is served as plain ES modules.

### On a Mac, inside an Ubuntu virtual machine

Fluidian runs the same in a VM as on bare metal. Any Ubuntu 22.04 or 24.04 guest works, ARM64 (Apple silicon) or x86-64, in UTM, Parallels, VMware Fusion, VirtualBox or Multipass. Inside the guest:

```bash
sudo apt update
sudo apt install -y python3 unzip
```

## 2. Unpack and check

```bash
unzip fluidian-1.2.0.zip
cd fluidian
./fluidian doctor
```

`doctor` prints what it found: Python, Node.js, a browser, each language toolchain, and whether an API key is set. Missing optional pieces are listed, not treated as errors.

## 3. Run the tests

```bash
./fluidian test --quick      # engine and runtime tests: a few seconds
./fluidian test              # everything, including each SDK whose toolchain is installed
bash scripts/test-all.sh     # the same, plus browser checks when Chrome is installed, with a one-line verdict
```

The run ends with a table and one of two lines: `All checks that could run have passed.` or a list of failures with their output. SDKs without a toolchain are shown as `SKIP`. To install the optional toolchains on Ubuntu or Debian:

```bash
scripts/install-toolchains.sh            # all of them
scripts/install-toolchains.sh go rust    # or only some
./fluidian test
```

## 4. Open the showcase and the gallery

Two applications ship with the framework. Both are ordinary Fluidian apps written in Python.

```bash
./fluidian showcase          # 85 complete screens: landing pages, storefronts, dashboards, AI products, mobile, modules
./fluidian gallery           # one page per AI capability family, the component library, portable logic and themes
```

Open <http://127.0.0.1:8787> in a browser inside the VM. To use the browser on the Mac instead, bind to all interfaces and use the VM's address:

```bash
./fluidian showcase --host 0.0.0.0
hostname -I                  # shows the VM's IP address; open http://<that address>:8787 on the Mac
```

In the showcase, add `?theme=midnight` (or any of the twenty-seven presets) to an address to see that screen in another theme, and `?platform=ios` or `?platform=android` to a `/mobile/…` address to switch the control skin.

In the gallery:

- **Live dashboard** — type `overdue over 5000, largest first` into the bar above the table.
- **Intelligent forms** — type `next friday 3pm` into *Pickup time* and press Tab.
- **Generative UI** — type `add a phone field` into a refine bar.
- **Intent bar** — press <kbd>Ctrl</kbd>+<kbd>K</kbd> anywhere and type `open the trust page`.
- **Portable logic** — add and tick to-do items; no request leaves the page.
- **Platform preview** — one wallet screen in the iOS skin, the Android skin and a second theme.
- **Developer tools** — press <kbd>Ctrl</kbd>+<kbd>.</kbd> to see the scene, the review and every AI call.

Everything works without an API key: answers come from the offline Reflex engine and are marked `AI · reflex`.

## 5. Write an app

Create `app.py` anywhere:

```python
from fluidian import AIError, App, ui

app = App("Notes")


@app.view
def view(ctx):
    page = ui.page(
        "Notes",
        ui.text_area("notes").prop("label", "Meeting notes").id("notes").ai("input.ghost").on("change", "set_notes"),
        ui.button("Summarise").prop("variant", "primary").on("click", "summarise"),
    )
    if "summary" in ctx.state:
        page.add(ui.callout(ctx.state["summary"]).prop("tone", "ai"))
    return page


@app.on("set_notes")
def set_notes(ctx, event):
    ctx.state["notes"] = event.value


@app.on("summarise")
def summarise(ctx, event):
    try:
        ctx.state["summary"] = ctx.ai("content.summarize", {"text": ctx.state.get("notes", "")})["title"]
    except AIError as error:
        ctx.toast(f"Could not summarise: {error}", "warning")


app.run()
```

Run it from the Fluidian directory:

```bash
./fluidian run /path/to/app.py
```

The view function is called whenever state changes; the engine diffs the result and updates the browser. The same app in the other thirteen languages is in the [SDK guide](sdks.md), and `./fluidian new <language> <directory>` scaffolds a starting point.

To get this app in another language, convert it:

```bash
./fluidian convert /path/to/app.py --to go,rust --probe
./fluidian run converted/go
```

## 6. Turn on models

```bash
bash scripts/set-api-key.sh      # asks for the key without showing it, and remembers it for new terminals
source ~/.fluidian/openai.env    # use it in this terminal straight away
./fluidian doctor --live
./fluidian gallery
```

Or, for the current terminal only: `export OPENAI_API_KEY=sk-...`. To forget a stored key: `bash scripts/set-api-key.sh --remove`.

`doctor --live` makes two small requests: it lists the models your account can reach, shows which one each tier will use, and performs one structured-output call. After that, results in the gallery are marked with the model that produced them instead of `reflex`.

To go back to offline answers without unsetting the key, add `--offline` or set `FLUIDIAN_OFFLINE=1`.

## 7. Where to go next

- [Why Fluidian](why.md) for what the framework removes from your work, and when not to use it.
- [Concepts](concepts.md) for the model behind what you just ran.
- [Portable logic](portable-logic.md) to put behaviour in the scene.
- [Converting between languages](convert.md) and [Cross-platform](cross-platform.md) to take one app everywhere.
- [Capability reference](reference/capabilities.md) to see what `.ai()` can attach.
- [Screens](gallery.md) for all 122 screens with their routes.
- [Testing](testing.md) to test your own app the way the SDKs are tested.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Address already in use` | Another process holds port 8787. Use `--port 8790`. |
| The page is blank from the Mac's browser | The engine is bound to 127.0.0.1 inside the VM. Start it with `--host 0.0.0.0`. |
| `403 Cross-origin request refused` | You are reaching the engine through a name it does not know. Set `FLUIDIAN_ALLOWED_HOSTS=your.host.name`. |
| An SDK shows `SKIP` | Its toolchain is not installed. Run `scripts/install-toolchains.sh <language>`. |
| The browser suite shows `SKIP` | No Chrome or Chromium was found. Install one (`sudo apt install -y chromium-browser`) or point `FLUIDIAN_BROWSER` at a binary. |
| The browser line says `cleared N leftover processes` | An earlier run was interrupted and left a test browser or test servers behind; this run removed them. Nothing to do. |
| A browser test fails with a block that starts `platform:` and `record folder:` | That block is what the clean-up could see on your system. Include it when you report the failure. |
| ``the application did not send a `ready` message`` | The app crashed on start or wrote something other than protocol messages to stdout. Run with `--trace` and read the lines printed from its stderr. |
| Results still say `reflex` with a key set | Run `./fluidian doctor --live`; it prints the provider's error. |
