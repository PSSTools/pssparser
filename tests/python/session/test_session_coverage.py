"""Every IParserSession method reaches every binding (core-in-leaf-plan.md
CF1.6). The session is the one place the lifecycle lives; a method one
binding cannot reach is a feature that binding will grow a copy of.

Read from source text, not from loaded modules, so the WASM wrapper is
checked without a WASM runtime. A method is covered by its own name, by its
JSON form (`markers` by `markersJson`), or by an alias below; anything else
needs an exemption that says why."""
import os
import re

import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _read(*p):
    with open(os.path.join(_REPO, *p)) as f:
        return f.read()


def _session_methods():
    text = _read("src", "include", "pssp", "IParserSession.h")
    body = text[text.index("class IParserSession {"):]
    names = re.findall(r"virtual\s+[\w:<>,\s\*&]+?\b(\w+)\s*\(", body)
    return [n for n in names if n != "IParserSession" and not n.startswith("~")]


def _python():
    text = _read("python", "core.pyx")
    body = text[text.index("cdef class ParserSession"):]
    return set(re.findall(r"^    (?:c?p?def|cdef \w+) (\w+)\(", body, re.M))


def _wasm():
    text = _read("wasm", "bindings.cpp")
    body = text[text.index('emscripten::class_<ParserSession>'):]
    return set(re.findall(r'\.function\("(\w+)"', body))


def _c():
    text = _read("src", "include", "pssp", "pssparser_c.h")
    snake = re.findall(r"\bpssp_session_(\w+)\s*\(", text)
    return {re.sub(r"_(\w)", lambda m: m.group(1).upper(), s) for s in snake}


#: Another name for the same thing, per binding.
ALIASES = {
    "python": {"root": "releaseRoot", "releaseUnits": "_takeUnits"},
    "wasm": {"units": "unitCount", "root": "hasRoot"},
    "c": {"units": "numUnits", "userUnits": "numUserUnits", "root": "hasRoot"},
}

#: Methods a binding does not reach, and why. An entry here is a decision.
EXEMPT = {
    "python": {
        "lintEngine": "Python lints through pssparser.lint, with an engine "
                      "of its own from Factory.mkLintEngine()",
    },
    "wasm": {
        "releaseUnits": "the session keeps the units: no JavaScript object owns them",
        "releaseRoot": "the session keeps the root; TypeScript reads a serialised copy",
        "userUnits": "TypeScript filters the materialised root by fileMap()",
        "resolveLocation": "lint-run markers are resolved in Lint.ts until CF6 "
                           "(core-in-leaf-plan.md CF1.3)",
        "lintEngine": "reached through the session's lint methods "
                      "(loadRuleFile, runLint, ...), not as an object",
    },
    "c": {
        "releaseUnits": "the session keeps the units: nothing on the C side owns them",
        "releaseRoot": "the tree does not cross to C yet (rust-binding R3)",
        "lintEngine": "no lint in the C interface yet",
    },
}

WRAPPERS = {"python": _python, "wasm": _wasm, "c": _c}


def test_the_session_has_methods():
    assert "parseSource" in _session_methods() and "link" in _session_methods()


@pytest.mark.parametrize("binding", sorted(WRAPPERS))
def test_every_session_method_is_reachable(binding):
    have = WRAPPERS[binding]()
    aliases = ALIASES.get(binding, {})
    exempt = EXEMPT.get(binding, {})
    missing = []
    for m in _session_methods():
        forms = {m, m + "Json", aliases.get(m, m)}
        if m.endswith("Json"):
            forms.add(m[:-len("Json")])
        if forms & have or m in exempt:
            continue
        missing.append(m)
    assert not missing, "%s does not reach %s" % (binding, missing)


@pytest.mark.parametrize("binding", sorted(WRAPPERS))
def test_exemptions_are_still_needed(binding):
    have = WRAPPERS[binding]()
    methods = set(_session_methods())
    for m in EXEMPT.get(binding, {}):
        assert m in methods, "%s: exemption for a method the session lacks: %s" % (binding, m)
        assert m not in have and m + "Json" not in have, \
            "%s now reaches %s; drop its exemption" % (binding, m)
