"""Check that the *installed* pssparser ships its agent skills correctly.

Run by every CI system test, against a venv holding only the built wheel:

    python scripts/check_wheel_skills.py

Linux also runs tests/python/skills (T5); Windows and macOS run only the
system test, so this is the one check of the skills in those wheels.  It
asserts what a consumer such as IVPM relies on (docs/design/agent-skills.md
§4): one ``agent.skills`` entry point per shipped skill, each returning an
absolute directory inside the installed package that holds a SKILL.md whose
``name`` is the entry-point name; no ``pssparser-dev``; and that resolving
them does not load the native libraries.

Deliberately imports nothing from the source tree: ``scripts/`` is on
sys.path, the repository's ``python/`` is not.
"""
import importlib.metadata as md
import os
import re
import sys

SHIPPED = {"pssparser", "pssparser-checkers", "pssparser-api"}


def main() -> int:
    import pssparser.skills
    pkg = os.path.dirname(os.path.abspath(pssparser.skills.__file__))
    share = os.path.join(pkg, "share", "skills")
    errors = []

    native = [m for m in ("pssparser.core", "pssparser.ast") if m in sys.modules]
    if native:
        errors.append(f"importing pssparser.skills loaded {native}")

    eps = {ep.name: ep for ep in md.distribution("pssparser").entry_points
           if ep.group == "agent.skills"}
    if set(eps) != SHIPPED:
        errors.append(f"agent.skills entry points are {sorted(eps)}, "
                      f"expected {sorted(SHIPPED)}")

    for name, ep in sorted(eps.items()):
        path = ep.load()()
        skill_md = os.path.join(path, "SKILL.md")
        if not (os.path.isabs(path) and os.path.isfile(skill_md)):
            errors.append(f"{name}: {path!r} is not a directory with SKILL.md")
            continue
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(share):
            errors.append(f"{name}: {path} is not under {share}")
        with open(skill_md, encoding="utf-8") as f:
            m = re.search(r"^name:\s*(\S+)\s*$", f.read(), re.M)
        if not m or m.group(1) != name:
            errors.append(f"{name}: SKILL.md name is {m and m.group(1)!r}")

    # Not a skill, but the same class of fault -- a path helper that is right
    # in the source tree and wrong in the wheel -- and this is the check that
    # runs against every platform's wheel.
    import pssparser
    for d in pssparser.get_incdirs():
        if not os.path.isfile(os.path.join(d, "pssp", "IFactory.h")):
            errors.append(f"get_incdirs() returned {d}, which has no pssp/IFactory.h")

    present = set(os.listdir(share)) if os.path.isdir(share) else set()
    if present != SHIPPED:
        errors.append(f"{share} holds {sorted(present)}, expected {sorted(SHIPPED)}")

    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print(f"Skills test PASSED: {', '.join(sorted(eps))} in {share}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
