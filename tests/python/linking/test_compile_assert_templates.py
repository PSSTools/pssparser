"""`compile assert` on a template parameter (symbol-resolution plan 8.5, F6).

A value parameter "can be referenced ... anywhere a constant expression is
allowed" in a generic's body (10.3.1 a), and LRM Ex. 71-73 assert on one. It
has a value only in a specialization, so the builder leaves such an
assertion alone, and each specialization checks its own copy once linked:
a failure is reported at the first use that creates the specialization
(PSS054), and the generic itself is never checked.
"""
import pssparser

from ..test_helpers import parse_collect


def messages(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"], m["message"]) for m in ms]


def related(code):
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    try:
        p.link()
    except Exception:
        pass
    return [[r["line"] for r in m.get("related", [])] for m in p.markers]


def test_each_specialization_is_checked_once():
    code = """\
component pss_top {
  struct S<int W = 8> { compile assert (W <= 32, "too wide"); bit[W] f; }
  S<16> a;
  S<64> b;
  S<64> c;
  S<> d;
}
"""
    assert messages(code) == [
        ("PSS054", 4, "compile assert failed for 'S<64>': too wide")]
    assert related(code) == [[2]]


def test_an_unused_generic_is_not_checked():
    code = """\
component pss_top {
  struct S<int W> { compile assert (W > 100); }
}
"""
    assert messages(code) == []


def test_lrm_example_72():
    code = """\
resource my_resource { }
component pss_top {
  pool[16] my_resource p;
  bind p *;
  action my_consumer_action <int n_locks = 4> {
    compile assert (n_locks in [1..16]);
    lock my_resource res[n_locks];
  }
  action t1 {
    activity {
      do my_consumer_action<2>;
      do my_consumer_action<17>;
      do my_consumer_action<>;
    }
  }
}
"""
    assert messages(code) == [
        ("PSS054", 12, "compile assert failed for 'my_consumer_action<17>'")]


def test_lrm_example_73_a_default_from_another_parameter():
    code = """\
component pss_top {
  action my_consumer_action <int width, bool is_wide = (width > 10) > {
    compile assert (width > 0);
    compile assert (!is_wide || width > 12, "wide needs more than 12");
  }
  action t1 {
    activity {
      do my_consumer_action<4>;
      do my_consumer_action<0>;
      do my_consumer_action<11>;
      do my_consumer_action<16>;
    }
  }
}
"""
    # The dependent default is folded into the name the message gives.
    assert messages(code) == [
        ("PSS054", 9, "compile assert failed for 'my_consumer_action<0,0>'"),
        ("PSS054", 10, "compile assert failed for 'my_consumer_action<11,1>': "
                       "wide needs more than 12")]


def test_lrm_example_71_generic_declarations():
    code = """\
struct my_template_s <type T> {
  T t_attr;
}
buffer my_buff_s <type T> {
  T t_attr;
}
abstract action my_consumer_action <int width, bool is_wide> {
  compile assert (width > 0);
}
component eth_controller_c <struct ifg_config_s, bool full_duplex = true> {
}
"""
    assert messages(code) == []


def test_a_parameter_shadows_a_constant_of_its_name():
    code = """\
const int W = 100;
component pss_top {
  struct S<int W> { compile assert (W < 50); }
  S<3> a;
  S<60> b;
}
"""
    assert [(c, l) for c, l, _ in messages(code)] == [("PSS054", 5)]


def test_a_condition_on_a_constant_is_still_evaluated_when_read():
    code = """\
component pss_top {
  static const int N = 4;
  struct S<int W> { compile assert (N > 8, "N too small"); }
}
"""
    assert messages(code) == [
        ("PSS054", 3, "compile assert failed: N too small")]


def test_a_condition_that_does_not_fold_in_a_specialization():
    code = """\
component pss_top {
  struct S<int W> { rand int x; compile assert (W > x); }
  S<4> a;
}
"""
    assert [(c, l) for c, l, _ in messages(code)] == [("PSS055", 3)]
