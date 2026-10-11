#!/usr/bin/env python3
#****************************************************************************
#* import_cel_conformance.py
#*
#* Converts cel-spec conformance files (tests/simple/testdata/*.textproto)
#* to JSON, for the lint engine's CEL tests (lint-core-plan.md C3.4).
#*
#*   import_cel_conformance.py [--spec DIR] [--out DIR] [file ...]
#*
#* --spec defaults to the ivpm package (packages/cel-spec/cel-spec-<ver>,
#* ivpm.yaml `default-dev`), --out to tests/data/cel-conformance/, the files
#* to DEFAULT_FILES. The output is committed; re-run after a cel-spec bump.
#*
#* The textproto files are read with a small text-format reader of our own,
#* so neither protobuf nor the cel-spec descriptors are needed: a test job
#* reads the JSON. Each output file is
#*
#*   {"source": "basic.textproto", "cel_spec": "<version>", "tests": [
#*       {"section": ..., "name": ..., "expr": ..., "fields": {...}}, ...]}
#*
#* where `fields` holds the rest of the test message (value, eval_error,
#* bindings, disable_check, ...) as parsed, for the test harness to interpret.
#*
#* The skip list (excluded features) belongs to the test harness, not here:
#* every test is converted, so the list can change without a re-import.
#****************************************************************************
import json
import os
import re
import subprocess
import sys

DEFAULT_FILES = [
    "basic", "comparisons", "logic", "lists", "macros", "string",
    "optionals", "parse", "integer_math", "fp_math", "conversions",
]


class TextProtoError(Exception):
    pass


_TOKEN = re.compile(r'''
    (?P<ws>\s+|\#[^\n]*)
  | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<ident>[A-Za-z_][A-Za-z0-9_.]*)
  | (?P<num>[-+]?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)[fFuU]?|[-]?inf|[-]?nan)
  | (?P<punct>[{}<>\[\]:,;/])
  | (?P<bad>.)
''', re.VERBOSE)


def _unescape(body):
    """Decodes a text-format string body (C escapes, octal and hex bytes,
    \\u and \\U) to bytes."""
    out = bytearray()
    i = 0
    simple = {'n': 10, 't': 9, 'r': 13, 'a': 7, 'b': 8, 'f': 12, 'v': 11,
              '\\': 92, "'": 39, '"': 34, '?': 63}
    raw = body.encode("utf-8")
    while i < len(raw):
        c = raw[i]
        if c != 0x5c:
            out.append(c)
            i += 1
            continue
        e = chr(raw[i + 1])
        if e in simple:
            out.append(simple[e])
            i += 2
        elif e in "01234567":
            j = i + 1
            v = 0
            while j < len(raw) and j < i + 4 and chr(raw[j]) in "01234567":
                v = v * 8 + (raw[j] - 48)
                j += 1
            out.append(v & 0xFF)
            i = j
        elif e in "xX":
            j = i + 2
            h = ""
            while j < len(raw) and len(h) < 2 and chr(raw[j]) in "0123456789abcdefABCDEF":
                h += chr(raw[j])
                j += 1
            out.append(int(h, 16))
            i = j
        elif e in "uU":
            n = 4 if e == "u" else 8
            cp = int(raw[i + 2:i + 2 + n].decode(), 16)
            out += chr(cp).encode("utf-8", "surrogatepass")
            i += 2 + n
        else:
            raise TextProtoError("unknown escape \\%s" % e)
    return bytes(out)


def _tokens(text):
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "bad":
            raise TextProtoError("unexpected %r at %d" % (m.group(), m.start()))
        yield kind, m.group()


class _Reader:
    def __init__(self, text):
        self.toks = list(_tokens(text))
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def message(self, close=None):
        msg = {}
        while True:
            kind, val = self.peek()
            if kind is None:
                if close:
                    raise TextProtoError("unterminated message")
                return msg
            if kind == "punct" and val == close:
                self.take()
                return msg
            if kind == "punct" and val in ",;":
                self.take()
                continue
            if kind == "punct" and val == "[":
                # extension / Any type URL: [type.googleapis.com/x.y]
                self.take()
                name = ""
                while self.peek()[1] != "]":
                    name += self.take()[1]
                self.take()
            elif kind == "ident":
                name = self.take()[1]
            else:
                raise TextProtoError("expected a field name, found %r" % val)
            if self.peek() == ("punct", ":"):
                self.take()
            value = self.value()
            msg.setdefault(name, []).append(value)

    def value(self):
        kind, val = self.peek()
        if kind == "punct" and val in "{<":
            self.take()
            return self.message("}" if val == "{" else ">")
        if kind == "punct" and val == "[":
            self.take()
            items = []
            while self.peek() != ("punct", "]"):
                if self.peek() == ("punct", ","):
                    self.take()
                    continue
                items.append(self.value())
            self.take()
            return items
        if kind == "str":
            data = b""
            while self.peek()[0] == "str":
                data += _unescape(self.take()[1][1:-1])
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return {"__bytes__": data.hex()}
        if kind in ("num", "ident"):
            self.take()
            return val
        raise TextProtoError("unexpected %r" % (val,))


def _single(msg, key, default=None):
    v = msg.get(key)
    return v[0] if v else default


def convert(path, version):
    with open(path, encoding="utf-8") as fp:
        root = _Reader(fp.read()).message()
    tests = []
    for section in root.get("section", []):
        sname = _single(section, "name", "")
        for t in section.get("test", []):
            fields = {k: v for k, v in t.items() if k not in ("name", "expr")}
            tests.append({
                "section": sname,
                "name": _single(t, "name", ""),
                "expr": _single(t, "expr", ""),
                "fields": fields,
            })
    return {"source": os.path.basename(path), "cel_spec": version, "tests": tests}


def _version(spec):
    """The cel-spec release: from git in a checkout, else from the directory
    name ivpm unpacks the release archive to (cel-spec-<ver>). Never from a
    git repository that merely encloses `spec`."""
    if os.path.isdir(os.path.join(spec, ".git")):
        try:
            return subprocess.run(
                ["git", "-C", spec, "describe", "--tags", "--always"],
                capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            pass
    m = re.match(r"cel-spec-(\d+\.\d+\.\d+.*)$", os.path.basename(os.path.abspath(spec)))
    return ("v" + m.group(1)) if m else "unknown"


def main(argv):
    import argparse
    import glob
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ap = argparse.ArgumentParser(description="Convert cel-spec conformance tests to JSON")
    ap.add_argument("--spec", help="cel-spec source tree (default: the ivpm package)")
    ap.add_argument("--out", default=os.path.join(root, "tests", "data", "cel-conformance"))
    ap.add_argument("files", nargs="*", default=DEFAULT_FILES)
    a = ap.parse_args(argv[1:])
    spec = a.spec
    if spec is None:
        found = sorted(glob.glob(os.path.join(root, "packages", "cel-spec", "cel-spec-*")))
        if len(found) != 1:
            ap.error("expected one packages/cel-spec/cel-spec-* (run `ivpm update`); "
                     "found %d. Use --spec." % len(found))
        spec = found[0]
    version = _version(spec)
    os.makedirs(a.out, exist_ok=True)
    for f in a.files:
        src = os.path.join(spec, "tests", "simple", "testdata", f + ".textproto")
        data = convert(src, version)
        with open(os.path.join(a.out, f + ".json"), "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=1, ensure_ascii=False)
            fp.write("\n")
        print("%-16s %4d tests  (cel-spec %s)" % (f, len(data["tests"]), version))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
