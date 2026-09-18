#!/usr/bin/env python3
"""Hand-authored controls for the cases `make_controls.py` could not repair.

Each body below is a case with its defect removed, written by hand.  The script
verifies every one of them parses *and links* clean before writing it, so an
unverified guess can never reach the corpus -- the same rule the automatic
search follows.

Kept in the tree rather than run once and discarded: these bodies are the
record of *why* each control looks the way it does, and they have to be re-run
whenever a case they cover is re-ported.

The search failed on these for two distinct reasons, both worth knowing:

* **The repair is structural.**  A construct in the wrong scope has to be
  moved, not patched; `class C {}` has to become `component C {}`; a reserved
  word used as a name has to be renamed.  No local token insertion reaches
  those.
* **The case has a latent second defect.**  Several ported cases assign to
  fields that were never declared (`x = 1;` in an `exec body` with no `int
  x;`).  pssparser never reports it, because the parse error stops the run
  before linking -- but the *control* links, so the control has to declare
  them.  A tool with better recovery would report both, which is a corpus wart
  to clean up when these classes are filled out (error-suite-plan.md X-2b).

Usage:  PYTHONPATH=python python3 error-suite/tools/manual_controls.py [--apply]
"""
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE))
from pss_errsuite.case import load_case  # noqa: E402

BODIES = {
# -- truncated / unclosed: close what was left open ---------------------------
"syntax/braces/truncated_mid_action_body.pss": """component C {
    action A {
        int x;
        exec body {
            x = 1;
        }
    }
}""",
"syntax/braces/unclosed_action_body.pss": """component C {
    action A {
        int x;
        exec body {
            x = 1;
        }
    }
}""",
# -- a missing ';' whose line also needs the field it assigns to --------------
"syntax/expr/expr_statement_missing_semicolon.pss": """component C {
    action A {
        int x;
        int y;
        exec body {
            x = 1;
            y = 2;
        }
    }
}""",
# -- foreign keywords --------------------------------------------------------
"syntax/keyword/class_instead_of_component.pss": """component C {
}""",
"syntax/keyword/extends_for_inheritance.pss": """component D {
}

component C : D {
}""",
"syntax/lex/stray_at_symbol_silent.pss": """component C {
}""",
# -- recovery pairs: repair both defects -------------------------------------
"syntax/recover/pair_keyword_field_name_two_structs.2.pss": """struct S {
    int a;
}

struct T {
    int b;
}""",
"syntax/recover/pair_missing_semicolon_two_actions.2.pss": """component C {
    action A {
        rand int x;
    }
    action B {
        rand int y;
    }
}""",
# -- reserved words as names: give them names --------------------------------
"syntax/reserved/keyword_as_action_name.pss": """component C {
    action a1 {
    }
}""",
"syntax/reserved/keyword_as_component_name.pss": """component c1 {
}""",
"syntax/reserved/keyword_as_enum_name.pss": """enum e1 {
    A, B
}""",
"syntax/reserved/keyword_as_package_name.pss": """package p1 {
}""",
"syntax/reserved/struct_named_component.pss": """struct s1 {
    int x;
}""",
# -- wrong scope: put the construct where it belongs -------------------------
"syntax/scope/action_at_file_scope.pss": """component C {
    action A {
    }
}""",
"syntax/scope/activity_at_file_scope.pss": """component C {
    action A {
    }
    action B {
        activity {
            do A;
        }
    }
}""",
"syntax/scope/component_decl_inside_action_body.pss": """component D {
}

component C {
    action A {
    }
}""",
"syntax/scope/package_inside_component.pss": """package P {
}

component C {
}""",
# -- statement heads ---------------------------------------------------------
"syntax/stmt/constraint_if_no_parens.pss": """component C {
    action A {
        rand int x;
        constraint {
            if (x == 1) {
                x == 2;
            }
        }
    }
}""",
"syntax/stmt/foreach_missing_colon.pss": """component C {
    action A {
    }
    action B {
        rand array<int, 4> arr;
        activity {
            foreach (a : arr) {
                do A;
            }
        }
    }
}""",
"syntax/stmt/foreach_no_parens.pss": """component C {
    action A {
    }
    action B {
        rand array<int, 4> arr;
        activity {
            foreach (a : arr) {
                do A;
            }
        }
    }
}""",
"syntax/stmt/if_missing_paren_close.pss": """component C {
    action A {
    }
    action B {
        rand int x;
        activity {
            if (x == 1) {
                do A;
            }
        }
    }
}""",
"syntax/stmt/if_no_parens_activity.pss": """component C {
    action A {
    }
    action B {
        rand int x;
        activity {
            if (x == 1) {
                do A;
            }
        }
    }
}""",
"syntax/stmt/repeat_count_missing_paren.pss": """component C {
    action A {
    }
    action B {
        activity {
            repeat (5) {
                do A;
            }
        }
    }
}""",
"syntax/stmt/repeat_while_missing_paren.pss": """component C {
    action A {
    }
    action B {
        rand int x;
        activity {
            repeat {
                do A;
            } while (x < 5);
        }
    }
}""",
# -- types -------------------------------------------------------------------
"syntax/type/enum_invalid_base_type_keyword.pss": """enum E : int {
    A, B
}""",
"syntax/type/inheritance_malformed_template_spec.pss": """component Base {
}

component C : Base {
}""",
}


def parses_clean(files):
    from pssparser import Parser
    from pssparser.parser import ParseException
    parser = Parser()
    try:
        parser.parses(files)
        parser.link()
    except ParseException:
        return parser, False
    except Exception as e:                       # pragma: no cover
        print("   !!", type(e).__name__, e)
        return parser, False
    return parser, not any(m.get("severity") == "error"
                           for m in parser.markers)


def main(apply: bool) -> int:
    bad = 0
    for rel, body in BODIES.items():
        path = SUITE / "cases" / rel
        case = load_case(path, SUITE / "cases")
        header = "".join(l + "\n" for l in case.source.splitlines()
                         if l.startswith("//!"))
        text = header + body + "\n"
        others = [(p.name, p.read_text())
                  for p in case.input_files() if p.name != path.name]
        parser, ok = parses_clean([(path.name, text)] + others)
        print(f"{'ok  ' if ok else 'FAIL'}  {rel}")
        if not ok:
            bad += 1
            for m in parser.markers[:3]:
                print(f"        {m['line']}:{m['col']} {m['message'][:70]}")
        elif apply:
            case.control_path.write_text(text)
    print(f"\n{len(BODIES) - bad}/{len(BODIES)} verified"
          + ("; written" if apply else "; dry run"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
