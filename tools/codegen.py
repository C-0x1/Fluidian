#!/usr/bin/env python3
"""Regenerate everything derived from the registries.

* ``spec/components.json`` and ``spec/capabilities.json``
* the component factories of all fourteen SDKs
* each SDK's conformance scene
* the golden conformance transcript (from the reference Python SDK)

Run via ``./fluidian codegen``.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from fluidian import codegen, components  # noqa: E402
from fluidian.kernel import catalog  # noqa: E402

UI = {"python": "fluidian/ui.py", "javascript": "ui.js", "typescript": "src/ui.ts", "go": "ui.go", "rust": "src/ui.rs",
      "java": "src/main/java/dev/fluidian/UI.java", "kotlin": "src/main/kotlin/dev/fluidian/UI.kt", "csharp": "Fluidian/UI.cs",
      "cpp": "include/fluidian/ui.hpp", "ruby": "lib/fluidian/ui.rb", "php": "src/UI.php", "dart": "lib/ui.dart",
      "elixir": "lib/fluidian/ui.ex", "lua": "fluidian_ui.lua"}
SCENE = {"python": "conformance_scene.py", "javascript": "conformance_scene.js", "typescript": "src/conformance_scene.ts",
         "go": "cmd/conformance/scene.go", "rust": "examples/conformance_scene.rs",
         "java": "src/examples/java/dev/fluidian/examples/ConformanceScene.java",
         "kotlin": "src/examples/kotlin/dev/fluidian/examples/ConformanceScene.kt", "csharp": "examples/Conformance/ConformanceScene.cs",
         "cpp": "examples/conformance_scene.hpp", "ruby": "conformance_scene.rb", "php": "conformance_scene.php",
         "dart": "bin/conformance_scene.dart", "elixir": "conformance_scene.exs", "lua": "conformance_scene.lua"}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main():
    write(os.path.join(ROOT, "spec", "components.json"), json.dumps(components.export_spec(), indent=1, ensure_ascii=False) + "\n")
    write(os.path.join(ROOT, "spec", "capabilities.json"), json.dumps(catalog(), indent=1, ensure_ascii=False) + "\n")
    for lang in codegen.LANGS:
        base = os.path.join(ROOT, "sdks", lang)
        write(os.path.join(base, UI[lang]), codegen.gen_ui(lang))
        write(os.path.join(base, SCENE[lang]), codegen.gen_conformance_scene(lang))
    from fluidian.testkit import conformance
    count = conformance.write_golden()
    print("codegen: %d components, %d capabilities, %d SDKs, golden transcript of %d messages" % (
        len(components.COMPONENTS), len(catalog()["capabilities"]), len(codegen.LANGS), count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
