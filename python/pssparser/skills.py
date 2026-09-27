"""Agent skills shipped with pssparser.

Each function here is an ``agent.skills`` entry point (see setup.py).  A
consumer such as IVPM calls it, in a subprocess of the target interpreter, and
links the returned directory into ``.claude/skills/``, ``.agents/skills/`` and
so on.  IVPM names the skill after the *entry-point name*, so there is one
entry point per skill and each name equals the skill's directory name and its
``SKILL.md`` frontmatter ``name``.

This module must stay cheap: it imports ``os`` only, and ``pssparser``'s
``__init__`` defers the native libraries, so discovery works even where they
fail to load.  See docs/design/agent-skills.md.
"""
import os

#: Skills shipped in the wheel.  pssparser-dev is deliberately absent: it is
#: for work on pssparser itself and lives in the repository's skills/ only.
SHIPPED = ("pssparser", "pssparser-checkers", "pssparser-api")


def _skill_dir(name: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    installed = os.path.join(here, "share", "skills", name)
    if os.path.isfile(os.path.join(installed, "SKILL.md")):
        return installed
    # Source tree or editable install: <repo>/skills/<name>, the same
    # directory IVPM's auto-probe finds, so the two dedupe by realpath.
    root = os.path.abspath(os.path.join(here, "..", ".."))
    return os.path.join(root, "skills", name)


def pssparser_skill() -> str:
    return _skill_dir("pssparser")


def checkers_skill() -> str:
    return _skill_dir("pssparser-checkers")


def api_skill() -> str:
    return _skill_dir("pssparser-api")
