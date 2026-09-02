import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--errors-full", action="store_true", default=False,
        help="E-7: run the exhaustive L2 mutation sweep (every operator x "
             "every token position x every source file) instead of the "
             "default fixed sample. Slow -- opt in explicitly.",
    )
    parser.addoption(
        "--bless-errors", action="store_true", default=False,
        help="E-8: regenerate the L3 rendered-output goldens "
             "(tests/python/errors/data/golden/*.txt) instead of asserting "
             "against them.",
    )


@pytest.fixture
def errors_full(request) -> bool:
    return request.config.getoption("--errors-full")


@pytest.fixture
def bless_errors(request) -> bool:
    return request.config.getoption("--bless-errors")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """E-7: mutants that still parsed cleanly are a separate finding (a more
    permissive grammar than the LRM), logged at low volume rather than
    failed -- see test_mutation_sweep.py."""
    from . import test_mutation_sweep as tms

    if tms._PERMISSIVE:
        terminalreporter.write_sep(
            "-", "E-7: mutants that still parsed cleanly (permissive grammar)"
        )
        for desc in tms._PERMISSIVE[:20]:
            terminalreporter.write_line(f"  {desc}")
        if len(tms._PERMISSIVE) > 20:
            terminalreporter.write_line(f"  ... and {len(tms._PERMISSIVE) - 20} more")

    if tms._DUPLICATE_MARKERS:
        terminalreporter.write_sep(
            "-", "E-7: exact-duplicate error markers collapsed (known-issues.md E7-D12)"
        )
        for desc in tms._DUPLICATE_MARKERS[:20]:
            terminalreporter.write_line(f"  {desc}")
        if len(tms._DUPLICATE_MARKERS) > 20:
            terminalreporter.write_line(f"  ... and {len(tms._DUPLICATE_MARKERS) - 20} more")

    if tms._KNOWN_CRASHES:
        terminalreporter.write_sep(
            "-", "E-7: known-issues.md E7-D14 recurrences (crash, not failed)"
        )
        for desc in tms._KNOWN_CRASHES[:20]:
            terminalreporter.write_line(f"  {desc}")
        if len(tms._KNOWN_CRASHES) > 20:
            terminalreporter.write_line(f"  ... and {len(tms._KNOWN_CRASHES) - 20} more")

    if tms._CASCADES:
        terminalreporter.write_sep(
            "-", "E-7: structural mutations whose fallout wasn't asserted on (not failed)"
        )
        for desc in tms._CASCADES[:20]:
            terminalreporter.write_line(f"  {desc}")
        if len(tms._CASCADES) > 20:
            terminalreporter.write_line(f"  ... and {len(tms._CASCADES) - 20} more")
