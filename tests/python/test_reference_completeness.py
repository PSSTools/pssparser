"""T-bind and T-miss: every reference is bound, and every undefined name is
reported (symbol-resolution-plan.md 3.6; INV-3 and INV-4).

Both are generated rather than written case by case, so a new kind of
reference is covered without anyone remembering to add a test for it:

T-bind
    Every reference node in the legal corpus -- found by walking each unit's
    owning fields from the AST schema, the ones the linker skips included --
    must be bound after linking. The corpus is every ``parses = true``
    pss-corpus bucket plus the error suite's accept cases, as
    ``scripts/refcov.py`` gathers it, and the files that link cleanly on their
    own are the subject. (A file that needs others to link, like the
    ``example2`` model, or that redefines the core library is not.)

T-miss
    One legal model with a slot for each reference field
    (``scripts/refcov_slots.py``). Each slot, filled with an undefined name,
    must produce an error on the slot's line. The schema test beside it
    requires every reference field to have a slot, so a new reference field
    with no probe fails here.

The measurements are ``scripts/refcov.py``'s, computed once and shared with
tests/python/test_reference_coverage.py, which pins the same numbers to a
baseline. That test catches any drift; this one says, per reference, what is
wrong and which plan item fixes it.

Every gap is listed below against the plan item that closes it. The T-miss
entries are strict xfails, and each T-bind exemption must still match a
reference, so closing a gap fails this module until its entry is removed.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import refcov  # noqa: E402
import refcov_slots  # noqa: E402


#: Reference kinds not bound yet on legal input, keyed by the field that owns
#: the reference or by the ``visit: false`` field it sits under (the walk's
#: origin). The value is the plan item that binds them.
UNBOUND = {
    "ActivitySchedulingConstraint.targets":
        "4.3: scheduling constraints name labelled sub-activities",
    "ComponentBind.pool_path":
        "4.5: pool binds resolve along component paths",
    "CovergroupCross.coverpoint_names": "10.1: the covergroup body scope",
    "CovergroupPortmap.name": "10.1: covergroup instantiation port maps",
    "CovergroupPortmap.target": "10.1: covergroup instantiation port maps",
    "CovergroupCoverpoint.target": "10.1: coverage expressions are not walked",
    "CovergroupCoverpoint.iff": "10.1: coverage expressions are not walked",
}

#: T-miss slots that are not reported yet, and the plan item that makes them.
SILENT = {
    "abind_lhs": "4.5: activity binds",
    "abind_lhs__member": "4.5: activity binds",
    "abind_rhs": "4.5: activity binds",
    "pool_bind_pool": "4.5: pool binds",
    "pool_bind_item__comp": "4.5: pool binds",
    "pool_bind_item__field": "4.5: pool binds",
    "sched_c": "4.3: scheduling-constraint targets",
    "slit_name": "8.9: struct-literal member names",
    "tag_field": "8.9: struct-literal member names (exec-block tag)",
    "ovr_inst": "U5: instance-override targets (no tracker item yet)",
    "ovr_inst__member": "U5: instance-override targets (no tracker item yet)",
    "bins_asize": "10.1: coverage", "bins_cpref": "10.1: coverage",
    "bins_range": "10.1: coverage", "bins_with": "10.1: coverage",
    "cg_opt_val": "10.1: coverage", "cgi_act": "10.1: coverage",
    "cgi_opt": "10.1: coverage", "cgi_port": "10.1: coverage",
    "cgi_pos": "10.1: coverage", "cp_iff": "10.1: coverage",
    "cp_target": "10.1: coverage", "cross_iff": "10.1: coverage",
    "cross_item": "10.1: coverage", "xbins_tgt": "10.1: coverage",
    "xbins_with": "10.1: coverage",
    # Legal, and rejected: "unknown type 'sa'" (F-N15).
    "pool_bind_item__subpath": "4.5: a pool bind through a component path",
}

#: Reference fields that cannot have a T-miss slot, and why.
NO_SLOT = {
    "ExprCompileHas.ref":
        "`compile has(x)` of an undefined x is legal (it is false), so "
        "there is nothing to report",
}


def _slot_params():
    """(job name, whether the variant is legal) for every slot, as
    ``refcov.tmiss`` names them."""
    out = [(k.lower(), False) for k in refcov_slots.BAD]
    for table, legal in ((refcov_slots.EXTRA, False), (refcov_slots.LEGAL, True)):
        for k in table:
            key, tag = k.split(":")
            out.append(("%s__%s" % (key.lower(), tag), legal))
    params = []
    for name, legal in out:
        marks = [pytest.mark.xfail(strict=True, reason=SILENT[name])] \
            if name in SILENT else []
        params.append(pytest.param(name, legal, id=name, marks=marks))
    return params


@pytest.fixture(scope="module")
def full():
    return refcov.compute_full()


# -- T-miss --------------------------------------------------------------------

@pytest.mark.parametrize("slot,legal", _slot_params())
def test_an_undefined_name_in_each_slot_is_reported(full, slot, legal):
    state = full["data"]["tmiss"][slot]
    if legal:
        assert state == "clean", \
            "the legal variant %s links with errors" % slot
    else:
        assert state == "reported", \
            "an undefined name in slot %s: %s, not reported on its line" \
            % (slot, state)


def test_every_silent_entry_is_a_slot():
    names = {p.values[0] for p in _slot_params()}
    assert not set(SILENT) - names, set(SILENT) - names


@pytest.mark.parametrize("field", sorted(refcov.ref_fields(refcov.load_schema())))
def test_every_reference_field_has_a_slot(full, field):
    """INV-4: a new reference field without a probe fails here. The fix is
    a slot in scripts/refcov_slots.py."""
    in_slots = full["data"]["schema_ref_fields"][field]["in_slots"]
    if field in NO_SLOT:
        assert not in_slots, "%s has a slot now: drop it from NO_SLOT" % field
    else:
        assert in_slots, "no T-miss slot exercises %s" % field


# -- T-bind --------------------------------------------------------------------

def _exemption(ref):
    ctx, _, _, origin = ref
    field = refcov._field_of_ctx(ctx)
    if field in UNBOUND:
        return field
    if origin in UNBOUND:
        return origin
    return None


def _unbound(full):
    """[(file, ref)] for every reference in a clean legal file that is not
    bound. ``dependent`` -- in a generic body, bound per specialization -- is
    not a failure."""
    out = []
    for fn, r in sorted(full["per_file"].items()):
        if not r["clean"]:
            continue
        for ref in r["refs"]:
            if ref[2] not in ("bound", "dependent"):
                out.append((fn, ref))
    return out


def test_every_reference_in_the_legal_corpus_is_bound(full):
    """INV-3 on legal input. ``unbound`` is a reference with no target;
    ``dead``, one whose target leads nowhere; ``noslot``, a name with
    nowhere to record a target."""
    if not (ROOT / "packages" / "pss-corpus" / "curated").is_dir():
        pytest.skip("pss-corpus is not present")
    bad = ["%s: %s (%s) is %s" % (fn, ref[0], ref[1], ref[2])
           for fn, ref in _unbound(full) if not _exemption(ref)]
    assert not bad, "\n".join(bad)


@pytest.mark.parametrize("key", sorted(UNBOUND))
def test_each_unbound_exemption_is_still_needed(full, key):
    if not (ROOT / "packages" / "pss-corpus" / "curated").is_dir():
        pytest.skip("pss-corpus is not present")
    assert any(_exemption(ref) == key for _, ref in _unbound(full)), (
        "nothing in the legal corpus is left unbound under %s any more: "
        "remove it from UNBOUND" % key)


def test_the_corpus_links_enough_files_to_mean_something(full):
    """T-bind covers only the files that link on their own. Pin that there
    are enough of them, so a regression that stops most files linking cannot
    pass as a clean T-bind."""
    if not (ROOT / "packages" / "pss-corpus" / "curated").is_dir():
        pytest.skip("pss-corpus is not present")
    assert full["data"]["bind"]["clean_files"] >= 50
