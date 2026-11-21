"""Generated SDK sources and published specs must match the registries they are generated from, and git must not hide them."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import support
from fluidian import codegen
from fluidian import components as C

BUILD_FOLDERS = ("node_modules", "target", "__pycache__", "_build", "dist", "out")
DOTNET_FOLDERS = ("bin", "obj")   # build output only where a .NET project is built: sdks/dart/bin holds source
BUILD_FILES = (".pyc", ".lock", ".class", ".jar")


def source_files():
    """Every file under sdks/ and spec/ that belongs in the repository, as a path from its root.

    Build output is left out, and so is anything whose name starts with a dot (tool caches, editor and system files).
    """
    for folder in ("sdks", "spec"):
        for base, dirs, files in os.walk(os.path.join(support.ROOT, folder)):
            rel = os.path.relpath(base, support.ROOT).replace(os.sep, "/")
            skip = BUILD_FOLDERS + (DOTNET_FOLDERS if (rel + "/").startswith("sdks/csharp/") else ())
            dirs[:] = sorted(d for d in dirs if d not in skip and not d.startswith("."))
            for name in sorted(files):
                if not name.startswith(".") and not name.endswith(BUILD_FILES):
                    yield "%s/%s" % (rel, name)


def tree_hash():
    digest = hashlib.sha256()
    for rel in source_files():
        path = os.path.join(support.ROOT, *rel.split("/"))
        digest.update(path.encode("utf-8"))
        with open(path, "rb") as fh:
            digest.update(fh.read())
    return digest.hexdigest()


def git_ignored(paths):
    """Those of ``paths`` that the ignore rules hide, each with the rule that hides it; ``None`` when git cannot be asked.

    The rules are read from the files as they are here, through a scratch repository of its own, so the answer is
    the same in a clone, in an unpacked archive and before a first commit: it is what ``git add`` would leave out.
    """
    git = shutil.which("git")
    if not git:
        return None
    scratch = tempfile.mkdtemp(prefix="fluidian-git-")
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_DIR=os.path.join(scratch, "repo"), GIT_WORK_TREE=support.ROOT)

        def run(*args, **kw):   # the developer's own global ignore file is not part of the repository
            return subprocess.run([git, "-c", "core.excludesFile=" + os.devnull] + list(args), cwd=support.ROOT, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, **kw)

        if run("init", "--quiet", "--template=").returncode != 0:   # no template: the scratch repository adds no rules of its own
            return None
        done = run("check-ignore", "--no-index", "--verbose", "-z", "--stdin", input="\0".join(paths).encode("utf-8"))
        if done.returncode not in (0, 1):   # 0: a rule matched, 1: none did; anything else is git failing
            return None
        field = done.stdout.decode("utf-8", "replace").split("\0")   # file, line, pattern and path for every match
        matches = [field[i:i + 4] for i in range(0, len(field) - 3, 4)]
        # a pattern that starts with "!" is an exception to a rule: the path it matches is kept, not hidden
        return {path: "%s:%s  %s" % (source, line, pattern) for source, line, pattern, path in matches if not pattern.startswith("!")}
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class CodegenTest(unittest.TestCase):
    def test_fourteen_languages(self):
        self.assertEqual(len(codegen.LANGS), 14)
        self.assertEqual(set(codegen.LANGS), {"python", "javascript", "typescript", "go", "rust", "java", "kotlin", "csharp", "cpp", "ruby", "php", "dart", "elixir", "lua"})

    def test_every_language_has_a_factory_for_every_component(self):
        for lang in codegen.LANGS:
            source = codegen.gen_ui(lang)
            for spec in C.COMPONENTS:
                self.assertIn('"%s"' % spec["type"] if lang not in ("php", "ruby", "dart", "lua", "elixir") else spec["type"], source, "%s lacks %s" % (lang, spec["type"]))

    def test_conformance_scene_covers_every_component(self):
        types = {n["type"] for n, _, _ in C.walk(C.normalize(codegen.conformance_scene())[0])}
        self.assertEqual(types, {c["type"] for c in C.COMPONENTS})

    def test_generated_files_are_current(self):
        before = tree_hash()
        done = subprocess.run([sys.executable, os.path.join(support.ROOT, "fluidian"), "codegen"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout.decode()[-500:])
        self.assertEqual(tree_hash(), before, "generated files were stale; `./fluidian codegen` has refreshed them, commit the result")

    def test_git_does_not_hide_a_source_file(self):
        """A file that .gitignore hides is present here and absent from every clone, where the suite then fails for want of it."""
        files = list(source_files())
        app = "sdks/dart/bin/conformance.dart"   # the file this happened to: `bin/` is build output only under sdks/csharp
        self.assertTrue(app in files, "%s is missing, or is no longer counted as source" % app)
        hidden = git_ignored(files)
        if hidden is None:
            self.skipTest("git is not installed, or could not be asked")
        self.assertEqual(hidden, {}, "hidden by the ignore rules, so `git add` leaves them out and no clone has them. Move the file, "
                         "or add an exception below the rule, as `!/sdks/dart/bin/` does:\n"
                         + "\n".join("  %s   (%s)" % item for item in sorted(hidden.items())))

    def test_published_capability_spec_is_current(self):
        with open(os.path.join(support.ROOT, "spec", "capabilities.json"), encoding="utf-8") as fh:
            published = json.load(fh)
        self.assertEqual(len(published["capabilities"]), 185)
        self.assertEqual([c["id"] for c in published["capabilities"]], list(support.CAPS))

    def test_scaffolds_compile_to_text_in_every_language(self):
        scene = {"type": "Page", "props": {"title": "Demo"}, "children": [{"type": "Button", "id": "go", "props": {"label": "Go"}, "on": {"click": "go"}}]}
        for lang in codegen.LANGS:
            source = codegen.emit_app(scene, lang, "Demo")
            self.assertIn("Demo", source, lang)
            self.assertIn("go", source, lang)


if __name__ == "__main__":
    unittest.main()
