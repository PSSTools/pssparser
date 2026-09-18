#!/usr/bin/env python3
"""A PSS "tool" whose output is dictated by the file it is given.

This is the keystone of the harness's test strategy: it gives the adapters,
runner and classifier a tool with *known* behaviour, so every harness test is
deterministic and none of them need pssparser (or any real PSS tool) to exist.

Directives live in ordinary `//` comments, so the fixture cases stay valid-ish
PSS and can be handed to a real tool too:

    //FAKE: emit 5:3 error "cannot assign 'string' to 'bit[8]'" code=FAKE001
    //FAKE: emit 5:3 error "…" end=9 related=2:5:"declared here"
    //FAKE: emit 5:3 error "…" fix=5:3-5:9:"x = 1;"
    //FAKE: hang                  -- sleep forever (tests the timeout kill)
    //FAKE: abort                 -- die by SIGSEGV (tests crash detection)
    //FAKE: traceback             -- print a Python traceback to stderr
    //FAKE: exit 3                -- exit with an undeclared code
    //FAKE: garbage               -- print unparseable noise on the JSON path

Usage: faketool.py [--json] [--max-errors N] [-pss] FILE...
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time

_EMIT_RE = re.compile(
    r'^emit\s+(?P<line>\d+):(?P<col>\d+)\s+(?P<severity>\w+)\s+'
    r'"(?P<message>(?:[^"\\]|\\.)*)"(?P<rest>.*)$')
# `key="quoted value"`, `key=1:1:"quoted label"`, or `key=bare`.
_KV_RE = re.compile(
    r'(\w+)=(?:"((?:[^"\\]|\\.)*)"'
    r'|(\d+:\d+:"(?:[^"\\]|\\.)*")'
    r'|(\S+))')


def parse_directives(path):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                stripped = raw.strip()
                if stripped.startswith("//FAKE:"):
                    out.append(stripped[len("//FAKE:"):].strip())
    except OSError as e:
        print(f"faketool: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)
    return out


def build(path, directives):
    diags = []
    for d in directives:
        if d == "hang":
            time.sleep(3600)
        elif d == "abort":
            # Suppress the core dump first: writing one can take seconds, long
            # enough that a short --timeout classifies the crash as a hang.
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            except (ImportError, ValueError, OSError):
                pass
            os.kill(os.getpid(), signal.SIGSEGV)
        elif d == "traceback":
            print("Traceback (most recent call last):\n  KaboomError",
                  file=sys.stderr)
            sys.exit(1)
        elif d == "garbage":
            print("faketool: internal notice; not JSON at all")
            sys.exit(1)
        elif d.startswith("exit "):
            sys.exit(int(d.split()[1]))
        m = _EMIT_RE.match(d)
        if not m:
            continue
        g = m.groupdict()
        entry = {
            "file": os.path.basename(path),
            "line": int(g["line"]),
            "col": int(g["col"]),
            "severity": g["severity"],
            "message": g["message"].replace('\\"', '"').replace("\\n", "\n"),
        }
        for key, quoted, located, bare in _KV_RE.findall(g["rest"] or ""):
            value = quoted or located or bare
            if key == "code":
                entry["code"] = value
            elif key == "end":
                entry["end_col"] = int(value)
            elif key == "suggestion":
                entry["suggestion"] = value
            elif key == "related":
                rl, rc, label = value.split(":", 2)
                entry.setdefault("related", []).append({
                    "file": os.path.basename(path), "line": int(rl),
                    "col": int(rc), "label": label.strip('"')})
        diags.append(entry)
    return diags


def main(argv):
    use_json = "--json" in argv
    max_errors = None
    files = []
    i = 0
    args = argv[:]
    while i < len(args):
        a = args[i]
        if a == "--json":
            pass
        elif a == "--max-errors":
            i += 1
            max_errors = int(args[i])
        elif a == "-pss":
            # Some real tools take a flag before *each* input file rather than
            # a bare list. Accepted here so the descriptors' `file_argv` option
            # has something to be exercised end to end against.
            i += 1
            files.append(args[i])
        elif a.startswith("--"):
            print(f"faketool: unknown option {a}", file=sys.stderr)
            return 2
        else:
            files.append(a)
        i += 1
    if not files:
        print("faketool: no input files", file=sys.stderr)
        return 2

    diags = []
    for path in files:
        diags.extend(build(path, parse_directives(path)))

    errors = [d for d in diags if d["severity"] == "error"]
    if max_errors is not None and max_errors > 0 and len(errors) > max_errors:
        keep, seen = [], 0
        for d in diags:
            if d["severity"] == "error":
                seen += 1
                if seen > max_errors:
                    continue
            keep.append(d)
        diags = keep
        errors = errors[:max_errors]

    if use_json:
        json.dump({"diagnostics": diags,
                   "summary": {"errors": len(errors),
                               "warnings": len(diags) - len(errors),
                               "files": len(files)}},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for d in diags:
            code = f"[{d['code']}] " if d.get("code") else ""
            print(f"{d['severity'].capitalize()}-{code}"
                  f"{d['file']}:{d['line']}:{d['col']}: {d['message']}")
            for r in d.get("related", ()):
                print(f"    {r['label']} at {r['line']}:{r['col']}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
