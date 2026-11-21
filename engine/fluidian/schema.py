"""Compact schema notation.

Capabilities describe their inputs and outputs in a terse notation that is
compiled to JSON Schema.  Output schemas are compiled in *strict* mode, which
matches the subset accepted by Structured Outputs (every property required,
``additionalProperties: false``, optional values expressed as nullable).

Notation
--------
``"str" | "num" | "int" | "bool"``   primitives (append ``?`` for nullable)
``"enum:a|b|c"``                      string enumeration (``enum?:`` nullable)
``"json"``                            a string holding a JSON-encoded value
``"node"``                            a scene node (transport encoding)
``"any"``                             unconstrained (input schemas only)
``[spec]``                            array
``{"key": spec, "opt?": spec}``       object; ``?`` marks an optional key
``(spec, "description")``             attaches a description
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

_PRIM = {"str": "string", "num": "number", "int": "integer", "bool": "boolean", "json": "string"}


def _nullable(sch: Dict[str, Any]) -> Dict[str, Any]:
    if "type" in sch and isinstance(sch["type"], str):
        out = dict(sch)
        out["type"] = [sch["type"], "null"]
        if "enum" in out and None not in out["enum"]:
            out["enum"] = list(out["enum"]) + [None]
        return out
    if "type" in sch:
        return sch
    return {"anyOf": [sch, {"type": "null"}]}


def _leaf(tok: str) -> Dict[str, Any]:
    if tok.startswith("enum"):
        head, _, body = tok.partition(":")
        out: Dict[str, Any] = {"type": "string", "enum": body.split("|")}
        return _nullable(out) if head.endswith("?") else out
    nullable = tok.endswith("?")
    if nullable:
        tok = tok[:-1]
    if tok == "node":
        out = {"$ref": "#/$defs/node"}
    elif tok == "any":
        out = {}
    elif tok in _PRIM:
        out = {"type": _PRIM[tok]}
        if tok == "json":
            out["description"] = "JSON-encoded value"
    else:
        raise ValueError("unknown schema token: %r" % tok)
    return _nullable(out) if nullable else out


def compile_schema(spec: Any, strict: bool = True) -> Dict[str, Any]:
    """Compile compact notation into JSON Schema."""
    if isinstance(spec, tuple):
        out = dict(compile_schema(spec[0], strict))
        out["description"] = spec[1]
        return out
    if isinstance(spec, str):
        return _leaf(spec)
    if isinstance(spec, list):
        return {"type": "array", "items": compile_schema(spec[0], strict) if spec else {}}
    if isinstance(spec, dict):
        props: Dict[str, Any] = {}
        required: List[str] = []
        for key, sub in spec.items():
            optional = key.endswith("?")
            name = key[:-1] if optional else key
            sch = compile_schema(sub, strict)
            if optional and strict:
                sch = _nullable(sch)
            props[name] = sch
            if strict or not optional:
                required.append(name)
        return {"type": "object", "properties": props, "required": required, "additionalProperties": not strict}
    raise TypeError("unsupported schema spec: %r" % (spec,))


def node_defs(types: List[str]) -> Dict[str, Any]:
    """Transport encoding of a scene node, safe for strict structured outputs."""
    return {
        "node": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": list(types)},
                "id": {"type": ["string", "null"]},
                "text": {"type": ["string", "null"], "description": "Primary text: title, label or content."},
                "action": {"type": ["string", "null"], "description": "Registered action bound to the component's main event."},
                "props": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string", "description": "JSON-encoded value"},
                        },
                        "required": ["key", "value"],
                        "additionalProperties": False,
                    },
                },
                "children": {"type": "array", "items": {"$ref": "#/$defs/node"}},
            },
            "required": ["type", "id", "text", "action", "props", "children"],
            "additionalProperties": False,
        }
    }


def uses_node(schema: Any) -> bool:
    if isinstance(schema, dict):
        if schema.get("$ref") == "#/$defs/node":
            return True
        return any(uses_node(v) for v in schema.values())
    if isinstance(schema, list):
        return any(uses_node(v) for v in schema)
    return False


def _type_ok(value: Any, name: str) -> bool:
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool) or (isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    if name == "null":
        return value is None
    return True


def validate(instance: Any, schema: Dict[str, Any], root: Optional[Dict[str, Any]] = None,
             path: str = "$", errors: Optional[List[str]] = None, limit: int = 12) -> List[str]:
    """Validate ``instance`` against the supported JSON Schema subset.

    Returns a list of human readable problems (empty when valid).
    """
    errors = [] if errors is None else errors
    root = root or schema
    if len(errors) >= limit:
        return errors
    ref = schema.get("$ref")
    if ref:
        target = root.get("$defs", {}).get(ref.rsplit("/", 1)[-1])
        if target is None:
            errors.append("%s: unresolved reference %s" % (path, ref))
            return errors
        return validate(instance, target, root, path, errors, limit)
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            if not validate(instance, option, root, path, [], limit):
                return errors
        errors.append("%s: does not match any allowed shape" % path)
        return errors
    stype = schema.get("type")
    if stype is not None:
        names = stype if isinstance(stype, list) else [stype]
        if not any(_type_ok(instance, n) for n in names):
            errors.append("%s: expected %s, got %s" % (path, "|".join(names), type(instance).__name__))
            return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r is not one of %s" % (path, instance, [e for e in schema["enum"] if e is not None]))
    if isinstance(instance, dict) and "properties" in schema:
        for name in schema.get("required", []):
            if name not in instance:
                errors.append("%s: missing required key %r" % (path, name))
        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in schema["properties"]:
                    errors.append("%s: unexpected key %r" % (path, name))
        for name, sub in schema["properties"].items():
            if name in instance:
                validate(instance[name], sub, root, "%s.%s" % (path, name), errors, limit)
    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(instance[:200]):
            validate(item, schema["items"], root, "%s[%d]" % (path, index), errors, limit)
    return errors


def _seeded(seed: str, salt: str) -> int:
    return int(hashlib.sha256((seed + "|" + salt).encode("utf-8")).hexdigest()[:8], 16)


def synthesize(schema: Dict[str, Any], seed: str = "", root: Optional[Dict[str, Any]] = None,
               name: str = "value", depth: int = 0, hint: Optional[str] = None) -> Any:
    """Build a deterministic instance that satisfies ``schema``.

    Used by the structural Reflex path and by the mock provider in tests.
    """
    root = root or schema
    ref = schema.get("$ref")
    if ref:
        target = root.get("$defs", {}).get(ref.rsplit("/", 1)[-1], {})
        if ref.endswith("/node"):
            return {"type": "Text", "id": None, "text": hint or "…", "action": None, "props": [], "children": []}
        return synthesize(target, seed, root, name, depth + 1, hint)
    if "anyOf" in schema:
        return synthesize(schema["anyOf"][0], seed, root, name, depth + 1, hint)
    if "enum" in schema:
        options = [e for e in schema["enum"] if e is not None]
        return options[_seeded(seed, name) % len(options)] if options else None
    stype = schema.get("type")
    if isinstance(stype, list):
        stype = next((t for t in stype if t != "null"), "null")
    if stype == "object":
        return {key: synthesize(sub, seed, root, key, depth + 1, hint)
                for key, sub in schema.get("properties", {}).items()}
    if stype == "array":
        if depth > 5:
            return []
        count = 1 + _seeded(seed, name + "#") % 2
        return [synthesize(schema.get("items", {}), seed + str(i), root, name, depth + 1, hint) for i in range(count)]
    if stype == "string":
        if schema.get("description") == "JSON-encoded value":
            return json.dumps(hint or "")
        base = (hint or "").strip()
        label = name.replace("_", " ")
        return base[:160] if base else label.capitalize()
    if stype == "integer":
        return 1 + _seeded(seed, name) % 5
    if stype == "number":
        return round(0.5 + (_seeded(seed, name) % 45) / 100.0, 2)
    if stype == "boolean":
        return True
    return None


def describe(schema: Dict[str, Any], root: Optional[Dict[str, Any]] = None, indent: int = 0) -> List[str]:
    """Render a schema as indented outline lines (used by the documentation generator)."""
    root = root or schema
    pad = "  " * indent
    lines: List[str] = []
    if schema.get("$ref"):
        return [pad + "scene node"]
    stype = schema.get("type")
    if isinstance(stype, list):
        stype = "|".join(stype)
    if "properties" in schema:
        for key, sub in schema["properties"].items():
            sub_type = sub.get("type")
            if isinstance(sub_type, list):
                sub_type = " | ".join(sub_type)
            if sub.get("$ref"):
                sub_type = "scene node"
            if "enum" in sub:
                sub_type = " | ".join(repr(e) for e in sub["enum"] if e is not None)
            if sub.get("type") == "array" or (isinstance(sub.get("type"), list) and "array" in sub["type"]):
                item = sub.get("items", {})
                if item.get("$ref"):
                    sub_type = "array of scene nodes"
                elif "properties" in item:
                    sub_type = "array of objects"
                else:
                    sub_type = "array of %s" % (item.get("type") or "values")
            desc = sub.get("description")
            lines.append("%s- `%s` — %s%s" % (pad, key, sub_type or "any", (". " + desc) if desc else ""))
            nested = sub.get("items") if sub.get("type") == "array" else sub
            if isinstance(nested, dict) and "properties" in nested:
                lines.extend(describe(nested, root, indent + 1))
    else:
        lines.append("%s- %s" % (pad, stype or "any"))
    return lines
