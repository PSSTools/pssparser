"""The flat C interface, libpssparser_c (pssp/pssparser_c.h), through ctypes:
the surface the Rust binding links (core-in-leaf-plan.md CF1.6)."""
import ctypes
import json
import os
import sys

import pytest

import pssparser

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

if sys.platform == "darwin":
    _LIBNAME = "libpssparser_c.dylib"
elif sys.platform == "win32":
    _LIBNAME = "pssparser_c.dll"
else:
    _LIBNAME = "libpssparser_c.so"


def _find_lib():
    # Beside the extension modules in a wheel; under build/ in a source tree
    # (the order pssparser.core's Factory.inst() looks in, reversed: the
    # package copy is the one a wheel test must exercise).
    cands = [os.path.join(os.path.dirname(pssparser.__file__), _LIBNAME)]
    cands += [os.path.join(_REPO, "build", d, _LIBNAME)
              for d in ("lib", "lib64", "bin", "src")]
    for c in cands:
        if os.path.isfile(c):
            return c
    raise AssertionError("%s not found in %s" % (_LIBNAME, cands))


@pytest.fixture(scope="module")
def lib():
    import pssparser.core  # the factory, loaded the way Python loads it
    pssparser.core.Factory.inst()
    so = ctypes.CDLL(_find_lib())
    P, I, S = ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p
    I32 = ctypes.c_int32
    sigs = {
        "pssp_c_abi_version": (I32, []),
        "pssp_session_new": (P, []),
        "pssp_session_free": (None, [P]),
        "pssp_session_last_error": (S, [P]),
        "pssp_session_set_max_errors": (None, [P, I32]),
        "pssp_session_set_collect_docstrings": (None, [P, I]),
        "pssp_session_get_collect_docstrings": (I, [P]),
        "pssp_session_set_collect_comments": (None, [P, I]),
        "pssp_session_get_collect_comments": (I, [P]),
        "pssp_session_set_enable_profiling": (None, [P, I]),
        "pssp_session_begin_parse": (I, [P]),
        "pssp_session_parse_source": (I, [P, S, S, ctypes.c_size_t]),
        "pssp_session_next_fileid": (I32, [P]),
        "pssp_session_num_units": (I32, [P]),
        "pssp_session_link": (I, [P]),
        "pssp_session_has_root": (I, [P]),
        "pssp_session_num_user_units": (I32, [P]),
        "pssp_session_num_markers": (I32, [P]),
        "pssp_session_num_call_markers": (I32, [P]),
        "pssp_session_markers_json": (S, [P]),
        "pssp_session_call_markers_json": (S, [P]),
        "pssp_session_clear_markers": (None, [P]),
        "pssp_session_has_errors": (I, [P]),
        "pssp_session_max_errors_exceeded": (I, [P]),
        "pssp_session_file_map_json": (S, [P]),
        "pssp_session_source_names_json": (S, [P]),
        "pssp_session_resolve_location": (S, [P, I32, I32, ctypes.POINTER(I32)]),
        "pssp_session_inactive_regions_json": (S, [P]),
        "pssp_session_profile_info_json": (S, [P]),
    }
    for name, (res, args) in sigs.items():
        f = getattr(so, name)
        f.restype = res
        f.argtypes = args
    so.sigs = sigs
    return so


@pytest.fixture
def session(lib):
    s = lib.pssp_session_new()
    assert s
    yield s
    lib.pssp_session_free(s)


def _parse(lib, s, name, text):
    b = text.encode()
    return lib.pssp_session_parse_source(s, name.encode(), b, len(b))


GOOD = "component pss_top {\n  action A { }\n}\n"
BAD_TYPE = "component pss_top {\n  action A { no_such_t f; }\n}\n"
COMPILE_IF = (
    "const int W = 8;\n"
    "component pss_top {\n"
    "  compile if (W > 16) { int wide_f; } else { int narrow_f; }\n"
    "}\n")


def test_every_declared_function_is_exported(lib):
    header = open(os.path.join(_REPO, "src", "include", "pssp", "pssparser_c.h")).read()
    import re
    declared = set(re.findall(r"\b(pssp_[a-z_]+)\s*\(", header))
    assert declared == set(lib.sigs), declared ^ set(lib.sigs)


def test_version(lib):
    assert lib.pssp_c_abi_version() == 1


def test_parse_and_link(lib, session):
    s = session
    lib.pssp_session_set_collect_docstrings(s, 1)
    assert lib.pssp_session_get_collect_docstrings(s) == 1
    lib.pssp_session_set_collect_comments(s, 1)
    assert lib.pssp_session_get_collect_comments(s) == 1
    assert lib.pssp_session_begin_parse(s) == 1
    assert lib.pssp_session_num_units(s) == 1          # the core library
    assert lib.pssp_session_next_fileid(s) == 1
    assert _parse(lib, s, "t.pss", COMPILE_IF) == 1
    assert json.loads(lib.pssp_session_source_names_json(s)) == {"1": "t.pss"}
    assert lib.pssp_session_link(s) == 1
    assert lib.pssp_session_has_root(s) == 1
    assert lib.pssp_session_num_user_units(s) == 1
    assert json.loads(lib.pssp_session_file_map_json(s)) == {"1": "t.pss"}
    regions = json.loads(lib.pssp_session_inactive_regions_json(s))
    assert [(r["fileid"], r["startLine"]) for r in regions] == [(1, 3)]
    assert lib.pssp_session_has_errors(s) == 0
    assert lib.pssp_session_max_errors_exceeded(s) == 0
    assert lib.pssp_session_profile_info_json(s) == b""   # after link


def test_markers(lib, session):
    s = session
    lib.pssp_session_set_max_errors(s, 0)
    assert lib.pssp_session_begin_parse(s) == 1
    assert _parse(lib, s, "b.pss", BAD_TYPE) == 1
    assert _parse(lib, s, "a.pss", BAD_TYPE) == 1
    assert lib.pssp_session_link(s) == 0
    assert lib.pssp_session_has_errors(s) == 1
    n = lib.pssp_session_num_markers(s)
    assert n >= 2 and lib.pssp_session_num_call_markers(s) == n
    markers = json.loads(lib.pssp_session_markers_json(s))
    assert len(markers) == n
    assert [m["file"] for m in markers] == sorted(m["file"] for m in markers)
    assert all(m["severity"] == "error" for m in markers)
    assert json.loads(lib.pssp_session_call_markers_json(s)) == markers
    lib.pssp_session_clear_markers(s)
    assert lib.pssp_session_num_markers(s) == 0


def test_a_failed_source(lib, session):
    s = session
    assert lib.pssp_session_begin_parse(s) == 1
    assert _parse(lib, s, "bad.pss", "component {") == 0
    assert lib.pssp_session_num_units(s) == 1
    assert lib.pssp_session_next_fileid(s) == 1


def test_resolve_location(lib, session):
    line = ctypes.c_int32()
    assert lib.pssp_session_resolve_location(session, -1, 4, ctypes.byref(line)) == b"<builtin>"
    assert line.value == 4
    assert lib.pssp_session_resolve_location(session, 9, 4, None) == b"<unknown>"


def test_misuse_is_an_error_not_a_crash(lib, session):
    assert _parse(lib, session, "t.pss", GOOD) == -1
    assert b"beginParse" in lib.pssp_session_last_error(session)


def test_profiling(lib, session):
    s = session
    lib.pssp_session_set_enable_profiling(s, 1)
    assert lib.pssp_session_begin_parse(s) == 1
    assert _parse(lib, s, "t.pss", GOOD) == 1
    assert "decisions" in json.loads(lib.pssp_session_profile_info_json(s))


def test_free_null_is_ignored(lib):
    lib.pssp_session_free(None)
