"""T-miss slots: one legal model with a reference in every slot we probe.

``BASE`` is a legal model with ``@@KEY@@`` placeholders. ``DEF`` fills each
with a legal name; ``BAD`` fills one at a time with an undefined one, and
``EXTRA`` holds further variants of a slot as ``KEY:tag``. A slot is
*reported* when linking the BAD variant yields an error on the slot's line.
See scripts/refcov.py and docs/design/symbol-resolution-plan.md §3.

Hand-authored for now: the plan's INV-4 wants the slots generated from the
AST schema. ``refcov.py`` reports which schema reference fields the legal
model exercises, which is the gap list for that work.

Promoted from the report F prototype (docs/design/symbol-resolution/tools/).
To add a slot: put ``@@KEY@@`` in BASE, and give KEY a legal value in DEF and
an undefined one in BAD. Then regenerate the baseline.
"""

BASE = r'''import std_pkg::*;
annotation ann_t { int v; }
struct tag_s { string nm; }
import class base_cls { void m(); }
import class cls : @@ICLS_BASE@@ { void n(); }
enum col_e { RED, GREEN@@ENUM_VAL@@ };
extend enum @@EXT_ENUM@@ { BLUE };
buffer buf_s { rand int d; }
resource res_s { }
struct gs <type T = int, int N = 1> { T f; }
struct base_s { rand int bf; }
component sub_c { action sa { lock res_s r; } }
component pss_top {
  import @@PKG_IMPORT@@::*;
  sub_c s1;
  pool buf_s bp;
  pool [@@POOL_SIZE@@] res_s rp;
  bind @@POOL_BIND_POOL@@ *;
  bind rp { @@POOL_BIND_ITEM@@ };
  typedef @@TYPEDEF_T@@ td_t;
  struct S : @@SUPER_T@@ { rand int a; rand bit[@@BIT_W@@] b; int arr[@@ARR_DIM@@]; int iv = @@FIELD_INIT@@; gs<@@TPARAM_T@@, @@TPARAM_V@@> g; }
  @@ANN@@
  action P { output buf_s o; lock res_s r; rand int px; }
  action C { input buf_s i; }
  action A {
    rand int x; rand bit[4] y; rand S s;
    constraint { @@CONSTR@@; }
    constraint { unique {x, @@UNIQUE@@}; default @@DEFAULT@@ == 1; default disable @@DEFAULT_DIS@@; }
    constraint { forall (it : @@FORALL_T@@) { it.x > 0; } }
    covergroup {
      option.weight = @@CG_OPT_VAL@@;
      cp_x : coverpoint @@CP_TARGET@@ iff (@@CP_IFF@@) {
        bins lo = [0..@@BINS_RANGE@@] with (@@BINS_WITH@@);
        bins ar[@@BINS_ASIZE@@] = [0..3];
        bins m = @@BINS_CPREF@@ with (x > 1);
      }
      @@CP_DT@@ cp_y : coverpoint y;
      xy : cross cp_x, @@CROSS_ITEM@@ iff (@@CROSS_IFF@@) { ignore_bins z = @@XBINS_TGT@@ with (@@XBINS_WITH@@); }
    } cg;
  }
  covergroup cg_t(int pa) { cpa : coverpoint pa; }
  action T {
    rand int tx; S sl;
    @@CGI_TYPE@@ ci(.@@CGI_PORT@@(@@CGI_ACT@@));
    cg_t cj(@@CGI_POS@@) with { option.weight = @@CGI_OPT@@; };
    P p1; C c1; A a1; A a2 {.@@HINIT_NAME@@ = 1};
    symbol sym(A h) { h; }
    activity {
      p1;
      c1;
      bind @@ABIND_LHS@@ c1.@@ABIND_RHS@@;
      @@TRAV_H@@;
      a1 with { @@TRAV_WITH@@ == 2; };
      do @@TRAV_T@@ with { x == 3; };
      do A { .@@INIT_DO@@ = 1 };
      a2 { .@@INIT_H@@ = @@INIT_VAL@@ };
      L1: parallel join_branch(@@JOIN_BRANCH@@) { L2: a1; a2; }
      schedule join_select(@@JOIN_SEL@@) { a1; a2; }
      constraint sequence { a1, @@SCHED_C@@ };
      @@SYM_CALL@@(@@SYM_ARG@@);
      repeat (@@REPEAT_CNT@@) { a1; }
      replicate (@@REPL_CNT@@) a1;
      foreach (@@AFOREACH@@) { a1; }
      select { (@@SEL_GUARD@@) [@@SEL_W@@] : a1; a2; }
      if (@@AIF@@) { a1; }
      match (@@AMATCH@@) { [1]: a1; default: a2; }
    }
    exec body {
      sl = { .@@SLIT_NAME@@ = 1, .b = @@SLIT_VAL@@ };
      @@PROC_LHS@@ = 1;
      tx = (@@CAST_T@@)tx;
      @@PROC_CALL@@();
      randomize @@RAND_TGT@@;
      foreach (e : @@PFOREACH@@) { tx += e; }
    }
    exec header C = @@TAG_T@@ { .@@TAG_FIELD@@ = "x" } : """ {{@@MUSTACHE@@}} """;
  }
  monitor M { A mh; activity { @@MON_TRAV@@; } }
  cv1 : cover @@COVER_REF@@;
  function void g(int p = @@FUNC_DFLT@@) { }
  function bit h() { return 1; }
  function void ifn(int a);
  export target function @@EXPORT_FUNC@@;
  import C function @@IMPORT_FUNC@@;
  override { type @@OVR_TYPE@@ with A; instance @@OVR_INST@@ with sub_c; }
}
extend component @@EXTEND_T@@ { }
export pss_top::@@EXPORT_ACTION@@();
'''
DEF = dict(ICLS_BASE='base_cls', ENUM_VAL='', EXT_ENUM='col_e', PKG_IMPORT='std_pkg', POOL_SIZE='2',
 POOL_BIND_POOL='bp', POOL_BIND_ITEM='s1.*, P.r', TYPEDEF_T='base_s', SUPER_T='base_s', BIT_W='4', ARR_DIM='4',
 FIELD_INIT='1', TPARAM_T='int', TPARAM_V='2', ANN='@ann_t { .v = 1 }', CONSTR='x > 0', UNIQUE='y', DEFAULT='x', DEFAULT_DIS='x',
 FORALL_T='A', CG_OPT_VAL='2', CP_TARGET='x', CP_IFF='x > 0', BINS_RANGE='3', BINS_WITH='x > 0', BINS_ASIZE='2', BINS_CPREF='cp_x',
 CP_DT='bit[4]', CROSS_ITEM='cp_y', CROSS_IFF='y > 0', XBINS_TGT='xy', XBINS_WITH='x == y', CGI_TYPE='cg_t', CGI_PORT='pa',
 CGI_ACT='tx', CGI_POS='tx', CGI_OPT='2', HINIT_NAME='x', ABIND_LHS='p1.o', ABIND_RHS='i', TRAV_H='a1', TRAV_WITH='x', TRAV_T='A',
 INIT_DO='x', INIT_H='x', INIT_VAL='1', JOIN_BRANCH='L2', JOIN_SEL='1', SCHED_C='a2', SYM_CALL='sym', SYM_ARG='a1',
 REPEAT_CNT='2', REPL_CNT='2', AFOREACH='sl.arr', SEL_GUARD='tx > 0', SEL_W='1', AIF='tx > 0', AMATCH='tx', SLIT_NAME='a', SLIT_VAL='2',
 PROC_LHS='tx', CAST_T='int', PROC_CALL='g', RAND_TGT='tx', PFOREACH='sl.arr', TAG_T='tag_s', TAG_FIELD='nm', MUSTACHE='tx',
 MON_TRAV='mh', COVER_REF='M', FUNC_DFLT='1', EXPORT_FUNC='h', IMPORT_FUNC='ifn', OVR_TYPE='A', OVR_INST='a1', EXTEND_T='pss_top', EXPORT_ACTION='T')
BAD = dict(ICLS_BASE='nosuch_cls', ENUM_VAL=' = NOSUCH', EXT_ENUM='nosuch_e', PKG_IMPORT='nosuch_pkg', POOL_SIZE='NOSUCH',
 POOL_BIND_POOL='nosuch_pool', TYPEDEF_T='nosuch_t', SUPER_T='nosuch_s', BIT_W='NOSUCH', ARR_DIM='NOSUCH', FIELD_INIT='NOSUCH',
 TPARAM_T='nosuch_t', TPARAM_V='NOSUCH', CONSTR='nosuch > 0', UNIQUE='nosuch', DEFAULT='nosuch', DEFAULT_DIS='nosuch', FORALL_T='nosuch_a',
 CG_OPT_VAL='NOSUCH', CP_TARGET='nosuch', CP_IFF='nosuch', BINS_RANGE='NOSUCH', BINS_WITH='nosuch > 0', BINS_ASIZE='NOSUCH',
 BINS_CPREF='nosuch_cp', CP_DT='nosuch_t', CROSS_ITEM='nosuch_cp', CROSS_IFF='nosuch', XBINS_TGT='nosuch_x', XBINS_WITH='nosuch == y',
 CGI_TYPE='nosuch_cg', CGI_PORT='nosuch_port', CGI_ACT='nosuch', CGI_POS='nosuch', CGI_OPT='NOSUCH', HINIT_NAME='nosuch',
 ABIND_LHS='nosuch.o', ABIND_RHS='nosuch', TRAV_H='nosuch', TRAV_WITH='nosuch', TRAV_T='nosuch_a', INIT_DO='nosuch', INIT_H='nosuch',
 INIT_VAL='nosuch', JOIN_BRANCH='NOLBL', JOIN_SEL='nosuch', SCHED_C='nosuch', SYM_CALL='nosuch_sym', SYM_ARG='nosuch',
 REPEAT_CNT='nosuch', REPL_CNT='nosuch', AFOREACH='nosuch', SEL_GUARD='nosuch', SEL_W='nosuch', AIF='nosuch', AMATCH='nosuch',
 SLIT_NAME='nosuch', SLIT_VAL='nosuch', PROC_LHS='nosuch', CAST_T='nosuch_t', PROC_CALL='nosuch_f', RAND_TGT='nosuch', PFOREACH='nosuch',
 TAG_T='nosuch_s', TAG_FIELD='nosuch', MUSTACHE='nosuch', MON_TRAV='nosuch', COVER_REF='NosuchM', FUNC_DFLT='NOSUCH',
 EXPORT_FUNC='nosuch_f', IMPORT_FUNC='nosuch_f', OVR_TYPE='nosuch_a', OVR_INST='nosuch', EXTEND_T='nosuch_c', EXPORT_ACTION='Nosuch',
 ANN='@nosuch_ann', )
EXTRA = {
 'POOL_BIND_ITEM:comp': 'nosuch.*, P.r', 'POOL_BIND_ITEM:atype': 's1.*, nosuch_a.r', 'POOL_BIND_ITEM:field': 's1.*, P.nosuch',
 'POOL_BIND_ITEM:subpath': 's1.sa.r, P.r',
 'ANN:pname': '@ann_t { .nosuch = 1 }', 'ANN:pval': '@ann_t { .v = NOSUCH }',
 'ABIND_LHS:member': 'p1.nosuch', 'OVR_INST:member': 'a1.nosuch',
 'CGI_ACT:legal': 'tx',
}
