"""Named sub-activities (LRM 11.8; symbol-resolution plan 4.3).

A label makes a named sub-activity. Paths walk labels, not blocks:
`b1.my_seq.my_rep.a` reaches the handle `a` declared directly under the
labeled `repeat`, although `my_rep` sits inside an unlabeled `parallel`
(11.8.3). A label is unique in its nearest labeled ancestor and does not
clash with a handle there (11.8.2). Labels used to be flattened into the
action scope, which accepted paths that skip a level and rejected the same
label in two sub-activities.

Decision Q4: a `replicate` exposes only its label array; a labeled
`if`/`select`/`match` exposes its branches' labels but not their handles;
monitor labels form no paths. Decision C-N4: on `T: a;`, `T.x` means `a.x`.
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"], m["message"]) for m in ms]


def bindings(code, *names):
    """(name, line of use, kind of declaration, line of its name) for each
    use of one of `names`."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.text, o.line, type(o.decl).__name__,
             o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text in names and not o.is_declaration]


EX124 = """\
component pss_top {
  action A { rand int x; };
  action B {
    A a;
    activity {
      a;
      my_seq: sequence {
        A a;
        a;
        parallel {
          my_rep: repeat (3) {
            A a;
            a;
          };
          sequence {
            A a;
            a;
          };
        };
      };
    };
  };
  action C {
    B b1, b2;
    constraint b1.a.x == 1;
    constraint b1.my_seq.a.x == 2;
    constraint b1.my_seq.my_rep.a.x == 3;
    activity {
      b1;
      b2 with { my_seq.my_rep.a.x == 4; };
    }
  };
}
"""


def test_lrm_example_124():
    assert markers(EX124) == []
    assert [b for b in bindings(EX124, "a", "my_seq", "my_rep") if b[1] >= 25] == [
        ("a", 25, "Field", 4),
        ("my_seq", 26, "ActivitySequence", 7), ("a", 26, "ActionHandleField", 8),
        ("my_seq", 27, "ActivitySequence", 7),
        ("my_rep", 27, "ActivityRepeatCount", 11),
        ("a", 27, "ActionHandleField", 12),
        ("my_seq", 30, "ActivitySequence", 7),
        ("my_rep", 30, "ActivityRepeatCount", 11),
        ("a", 30, "ActionHandleField", 12)]


def test_a_path_may_not_skip_a_level():
    """`my_rep` is reachable only as `my_seq.my_rep` (11.8.3)."""
    code = EX124.replace("b1.my_seq.my_rep.a.x == 3", "b1.my_rep.a.x == 3")
    assert markers(code) == [("PSS002", 27, "'b1' has no member named 'my_rep'; did you mean 'my_seq'?")]


EX115 = """\
component pss_top {
  action A { rand int x; }
  action B { }
  action C { }
  action my_compound {
    rand int in [2..4] count;
    activity {
      parallel {
        replicate (count) RL[]: {
          A a;
          B b;
          a;
          b;
        }
      }
      if (RL[count-1].a.x == 0) {
        do C;
      }
    }
  };
  action my_test {
    activity {
      do my_compound with {
        RL[0].a.x == 10;
      };
    }
  };
}
"""


def test_lrm_example_115_label_arrays():
    """`RL[k]` names the k-th expansion of the body, from inside the activity
    and from outside the action (11.5.1.1 e)."""
    assert markers(EX115) == []
    assert [b for b in bindings(EX115, "RL", "a") if b[1] in (16, 24)] == [
        ("RL", 16, "ActivitySequence", 9), ("a", 16, "ActionHandleField", 10),
        ("RL", 24, "ActivitySequence", 9), ("a", 24, "ActionHandleField", 10)]


def test_lrm_example_82_a_label_under_unlabeled_statements():
    """`xfer` is under an unlabeled `repeat` and `select`, so it belongs to
    the action (11.8.2)."""
    code = """\
component mem_c { action load_buff {} }
component dma_c { action mem2mem_xfer { rand int size; } }
component cpu_c { action memcpy { rand int size; } }
component pss_top {
  mem_c m; dma_c d; cpu_c c;
  action mem2mem_chain {
    activity {
      do mem_c::load_buff;
      repeat (10) {
        select {
          xfer: do dma_c::mem2mem_xfer;
          cpy: do cpu_c::memcpy;
        }
      }
    }
  }
  action my_test {
    activity {
      do mem2mem_chain with { xfer.size > 10; };
    }
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "xfer", "size") == [
        ("xfer", 19, "ActivityActionTypeTraversal", 11), ("size", 19, "Field", 2)]


def test_lrm_example_94_join_branch_under_a_labeled_parallel():
    """`L2` is in `L1`'s named sub-activity, not the action's; `join_branch`
    finds it from its own block."""
    code = """\
component pss_top {
  action A {} action B {} action C {} action D {} action F {}
  action T {
    B b[2];
    activity {
      L1: parallel join_branch(L2) {
        L2: parallel {
          L3: do A;
          L4: parallel join_branch (L5) {
            L5: b[0];
            L6: do C;
          }
        }
        L7: do D;
      }
      L8: do F;
    }
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "L2", "L5") == [
        ("L2", 6, "ActivityParallel", 7),
        ("L5", 9, "ActivityActionHandleTraversal", 10)]


def test_lrm_example_123_scheduling_constraint_targets():
    code = """\
component pss_top {
  action A1 { rand int x; }
  action B1 { rand int x; }
  action B { activity { L: schedule { A1 a; B1 b; a; b; } } constraint parallel {L.a, L.b}; }
}
"""
    assert markers(code) == []
    assert [b for b in bindings(code, "L", "a", "b") if b[2] != "ActionHandleField"
            or b[3] == 4] == [
        ("a", 4, "ActionHandleField", 4), ("b", 4, "ActionHandleField", 4),
        ("L", 4, "ActivitySchedule", 4), ("a", 4, "ActionHandleField", 4),
        ("L", 4, "ActivitySchedule", 4), ("b", 4, "ActionHandleField", 4)]


def test_a_scheduling_constraint_target_is_checked():
    code = """\
component pss_top {
  action A1 { rand int x; }
  action B { activity { L: schedule { A1 a; a; } } constraint parallel {L.nosuch, Q.b}; }
}
"""
    assert [(c, ln) for (c, ln, _) in markers(code)] == [("PSS002", 3), ("PSS002", 3)]


def test_the_same_label_in_two_sub_activities():
    """Legal: each `X` is unique in its own named sub-activity (11.8.2)."""
    code = """\
component pss_top {
  action A { rand int x; }
  action B { activity { L1: { X: do A; } L2: { X: do A; } } }
  action C { B b; constraint b.L1.X.x == 1; constraint b.L2.X.x == 2; activity { b; } }
}
"""
    assert markers(code) == []


def test_a_label_visible_from_inside_its_sub_activity():
    code = """\
component pss_top {
  action A { rand int x; }
  action B { activity { L1: sequence { T: do A; do A with { x == T.x; }; } } }
}
"""
    assert markers(code) == []
    assert bindings(code, "T") == [("T", 3, "ActivityActionTypeTraversal", 3)]


# -- 11.8.2 label rules --------------------------------------------------------

def test_lrm_example_122_conflicting_labels():
    """The `if` is not labeled, so both `L2`s are in `L1`."""
    code = """\
component pss_top {
  action A {};
  action B {
    int x;
    activity {
      L1: parallel {
        if (x > 10) {
          L2: { A a; a; }
          { A a; a; }
        }
        L2: { A a; a; }
      }
    }
  };
}
"""
    assert markers(code) == [("PSS003", 11, "duplicate declaration of 'L2'")]


def test_lrm_example_123_label_clashes_with_a_handle():
    code = """\
component pss_top {
  action A {} action B {} action C {} action D {}
  action X {
    activity {
      L: schedule {
        A a;
        B b;
        a: {
          do C;
          do D;
        }
      }
    }
    constraint parallel {L.a, L.b};
  }
}
"""
    assert markers(code) == [("PSS003", 8, "duplicate declaration of 'a'")]


# -- Decision Q4 ---------------------------------------------------------------

def test_a_labeled_if_exposes_labels_but_not_handles():
    code = """\
component pss_top {
  action A { rand int x; }
  action B { activity { I: if (1) { A h; h; L: do A; } } }
  action C { B b; constraint b.I.L.x == 1; constraint b.I.h.x == 1; activity { b; } }
}
"""
    assert markers(code) == [("PSS002", 4, "'I' has no member named 'h'")]


def test_a_replicate_exposes_only_its_label_array():
    code = """\
component pss_top {
  action A { rand int x; }
  action B { activity { R: replicate (2) { A h; h; } } }
  action D { activity { R: replicate (2) RL[]: { A h; h; } } }
  action C {
    B b; D d;
    constraint b.R.h.x == 1;
    constraint d.R.RL[1].h.x == 1;
    activity { b; d; }
  }
}
"""
    assert markers(code) == [("PSS002", 7, "'R' has no member named 'h'")]


def test_monitor_labels_form_no_paths():
    code = """\
component pss_top {
  action A { rand int x; }
  monitor M { A a; activity { a; S: sequence { A a; a; } } }
  monitor N { M m1; constraint m1.S.a.x == 1; activity { m1; } }
}
"""
    assert markers(code) == [("PSS002", 4, "'m1' has no member named 'S'")]


# -- Decision C-N4 -------------------------------------------------------------

def test_a_labeled_handle_traversal_names_the_handle():
    """In either order: the constraint may come before the activity."""
    for body in ("activity { T: a; } constraint T.x < 3;",
                 "constraint T.x < 3; activity { T: a; }"):
        code = """\
component pss_top {
  action A { rand int x; }
  action B { A a; %s }
}
""" % body
        assert markers(code) == []
        assert bindings(code, "x")[-1] == ("x", 3, "Field", 2)


def test_a_labeled_handle_traversal_reports_an_unknown_member():
    code = """\
component pss_top {
  action A { rand int x; }
  action B { A a; activity { T: a; } constraint T.nosuch < 3; }
}
"""
    assert markers(code) == [("PSS002", 3, "'T' has no member named 'nosuch'")]


def test_a_label_path_into_an_action_declared_later():
    """`a`'s type is not bound until `T2` is resolved, after `T`; the path is
    retried then, in the `with` block's type."""
    code = """\
component pss_top {
  action A { rand int x; }
  action T { activity { do T2 with { RL[0].a.x == 10; }; } }
  action T2 { activity { replicate (2) RL[]: { A a; a; } } }
}
"""
    assert markers(code) == []
    assert bindings(code, "x")[-1] == ("x", 3, "Field", 2)
    code = code.replace("RL[0].a.x", "RL[0].a.nosuch")
    assert markers(code) == [("PSS002", 3, "'a' has no member named 'nosuch'")]
