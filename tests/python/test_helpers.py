"""
Shared test utilities and helpers for PSS frontend tests
"""
from typing import Optional, List, Tuple, Any
from pssparser import Parser
from pssparser.core import Factory
from pssparser.utils import SymbolScopeUtil, SymbolTypeScopeUtil


# =============================================================================
# Parsing Helpers
# =============================================================================

def parse_pss(code: str, filename: str = "test.pss", parser: Optional[Parser] = None) -> Any:
    """
    Parse PSS code and return linked symbol tree
    
    Args:
        code: PSS source code
        filename: Filename for error reporting
        parser: Optional parser instance (creates new if None)
        
    Returns:
        Linked symbol scope root
        
    Raises:
        Exception if parsing or linking fails
    """
    if parser is None:
        parser = Parser()
    
    parser.parses([(filename, code)])
    return parser.link()


def parse_multi_file(files: List[Tuple[str, str]], parser: Optional[Parser] = None) -> Any:
    """
    Parse multiple PSS files and return linked symbol tree
    
    Args:
        files: List of (filename, code) tuples
        parser: Optional parser instance
        
    Returns:
        Linked symbol scope root
    """
    if parser is None:
        parser = Parser()
    
    parser.parses(files)
    return parser.link()


# =============================================================================
# Symbol Access Helpers
# =============================================================================

def get_symbol(scope, name: str):
    """
    Get symbol by name from scope
    
    Args:
        scope: Symbol scope to search
        name: Symbol name (supports qualified names with ::)
        
    Returns:
        Symbol object or None if not found
    """
    if scope is None:
        return None
    
    util = SymbolScopeUtil(scope)
    
    if '::' in name:
        # Qualified name lookup
        return util.getQname(name)
    else:
        # Simple name lookup in current scope
        if scope.symtabHas(name):
            idx = scope.symtabAt(name)
            return scope.getChild(idx)
    return None


def has_symbol(scope, name: str) -> bool:
    """
    Check if symbol exists in scope
    
    Args:
        scope: Symbol scope to search
        name: Symbol name
        
    Returns:
        True if symbol exists, False otherwise
    """
    return get_symbol(scope, name) is not None


def get_type_scope_util(scope):
    """Get SymbolTypeScopeUtil for a scope"""
    return SymbolTypeScopeUtil(scope)


# =============================================================================
# Location Helpers
# =============================================================================

def get_location(node) -> Optional[Tuple[int, int]]:
    """
    Get source location from AST node
    
    Args:
        node: AST node
        
    Returns:
        Tuple of (line, column) or None if no location
    """
    if node is None:
        return None
    
    if hasattr(node, 'getLocation'):
        loc = node.getLocation()
        return (loc.lineno, loc.linepos)
    return None


def assert_location(node, line: int, col: int):
    """
    Assert node has expected source location
    
    Args:
        node: AST node
        line: Expected line number
        col: Expected column number
        
    Raises:
        AssertionError if location doesn't match
    """
    loc = get_location(node)
    assert loc is not None, f"Node has no location information"
    assert loc[0] == line and loc[1] == col, \
        f"Expected location ({line}, {col}), got {loc}"


# =============================================================================
# Assertion Helpers
# =============================================================================

def assert_parse_ok(code: str, parser_or_filename=None) -> Any:
    """
    Assert code parses without errors
    
    Args:
        code: PSS source code
        parser_or_filename: Optional Parser instance or filename string
        
    Returns:
        Linked symbol scope root
        
    Raises:
        AssertionError if parsing fails
    """
    if isinstance(parser_or_filename, Parser):
        root = parse_pss(code, parser=parser_or_filename)
    elif isinstance(parser_or_filename, str):
        root = parse_pss(code, filename=parser_or_filename)
    else:
        root = parse_pss(code)
    assert root is not None, "Parse failed - returned None"
    return root


def assert_parse_error(code: str, expected_error: Optional[str] = None):
    """
    Assert code fails to parse with expected error
    
    Args:
        code: PSS source code that should fail
        expected_error: Optional substring expected in error message
        
    Raises:
        AssertionError if parsing succeeds or error doesn't match
    """
    try:
        parse_pss(code)
        assert False, "Expected parse error but parsing succeeded"
    except Exception as e:
        if expected_error:
            error_msg = str(e)
            assert expected_error in error_msg, \
                f"Expected error containing '{expected_error}', got: {error_msg}"


def assert_linked(scope, name: str):
    """
    Assert symbol is linked in scope
    
    Args:
        scope: Symbol scope
        name: Symbol name to check
        
    Returns:
        The found symbol
        
    Raises:
        AssertionError if symbol not found
    """
    sym = get_symbol(scope, name)
    assert sym is not None, f"Symbol '{name}' not found or not linked"
    return sym


def assert_no_errors(parser: Parser):
    """
    Assert parser has no error-severity markers

    Args:
        parser: Parser to check

    Raises:
        AssertionError if parser has errors
    """
    errors = [m for m in parser.markers if m.get("severity") == "error"]
    assert not errors, \
        "Expected no errors, got:\n" + _format_markers(errors)


# =============================================================================
# Marker (diagnostic) Helpers
# =============================================================================
#
# Marker IDs (PSSnnn) are not carried by the C++ marker objects. They are
# assigned in Python by matching the message text -- see
# pssparser.cli.commands._assign_core_code. These helpers route markers through
# that same mapping so a test asserting on an ID exercises the mapping the CLI
# uses, rather than a parallel copy of it.


def _assign_codes(markers: List[dict]) -> List[dict]:
    """Annotate markers with their 'code' (PSSnnn) field where one is known."""
    from pssparser.cli.commands import _assign_core_code
    return [_assign_core_code(m) for m in markers]


# Every marker any parse_collect() call in the session has produced. E-2's
# global lints (tests/python/errors/test_message_lints.py) assert invariants
# over this instead of hooking each call site individually, so a lint applies
# to every test that goes through parse_collect regardless of which directory
# it lives in.
ALL_MARKERS: List[dict] = []

# Same markers, grouped by the parse_collect() call that produced them --
# needed for invariants that only make sense within one parse (e.g. "markers
# from a single parse are emitted in (file, line, col) order"), which a flat
# merge across unrelated test cases would not let you check.
ALL_MARKER_BATCHES: List[List[dict]] = []


def _format_markers(markers: List[dict]) -> str:
    """Render a marker list for assertion failure messages."""
    if not markers:
        return "    (none)"
    return "\n".join(
        "    [%s] %s (%s:%s:%s)%s" % (
            m.get("severity", "?"),
            m.get("message", ""),
            m.get("file", "?"),
            m.get("line", "?"),
            m.get("col", "?"),
            " code=%s" % m["code"] if m.get("code") else "")
        for m in markers)


def parse_collect(code: str, filename: str = "test.pss",
                  parser: Optional[Parser] = None,
                  max_errors: Optional[int] = None) -> Tuple[Any, List[dict]]:
    """
    Parse and link, returning (root_or_None, markers) instead of raising.

    This is the primitive the marker assertions are built on. Diagnostics that
    do not stop the parse (warnings, hints, info) are only reachable this way --
    parse_pss raises before the caller can inspect them.

    Args:
        code: PSS source code
        filename: Filename for error reporting
        parser: Optional parser instance (creates new if None)
        max_errors: When given, applied via Parser.set_max_errors before
            parsing (0 = unlimited). None leaves the Parser's own default
            (unlimited) untouched -- so a caller-supplied `parser` that
            already has a cap keeps it.

    Returns:
        (root, markers) where root is the linked symbol scope, or None if
        parsing/linking failed. markers is a list of marker dicts, each
        annotated with a 'code' key where an ID is known.
    """
    if parser is None:
        parser = Parser()

    if max_errors is not None:
        parser.set_max_errors(max_errors)

    try:
        parser.parses([(filename, code)])
        root = parser.link()
    except Exception as e:
        # ParseException carries the markers that triggered it. Anything else
        # is a bug in the parser rather than a diagnostic, so surface it.
        markers = getattr(e, "markers", None)
        if markers is None:
            raise
        coded = _assign_codes(markers)
        ALL_MARKERS.extend(coded)
        ALL_MARKER_BATCHES.append(coded)
        return None, coded

    coded = _assign_codes(parser.markers)
    ALL_MARKERS.extend(coded)
    ALL_MARKER_BATCHES.append(coded)
    return root, coded


def find_markers(markers: List[dict], marker_id: Optional[str] = None,
                 severity: Optional[str] = None,
                 text: Optional[str] = None) -> List[dict]:
    """
    Filter a marker list by ID, severity, and/or message substring.

    Args:
        markers: Marker list, as returned by parse_collect
        marker_id: Expected marker code (e.g. "PSS002"); None matches any
        severity: Expected severity ("error"/"warning"/"info"/"hint")
        text: Substring expected in the message (case-insensitive)

    Returns:
        The matching subset, in emission order
    """
    result = markers
    if marker_id is not None:
        result = [m for m in result if m.get("code") == marker_id]
    if severity is not None:
        result = [m for m in result if m.get("severity") == severity]
    if text is not None:
        needle = text.lower()
        result = [m for m in result if needle in m.get("message", "").lower()]
    return result


def assert_marker(code: str, marker_id: Optional[str] = None,
                  severity: Optional[str] = None,
                  text: Optional[str] = None,
                  count: Optional[int] = None) -> dict:
    """
    Assert a marker matching the given criteria was emitted.

    At least one of marker_id/severity/text must be given -- an unconstrained
    call would assert only that *some* diagnostic occurred, which is never what
    a test means.

    Args:
        code: PSS source code
        marker_id: Expected marker code (e.g. "PSS002")
        severity: Expected severity ("error"/"warning"/"info"/"hint")
        text: Substring expected in the message (case-insensitive)
        count: If given, the exact number of matches expected

    Returns:
        The first matching marker

    Raises:
        AssertionError if no marker matches (or count does not match)
    """
    assert marker_id is not None or severity is not None or text is not None, \
        "assert_marker requires at least one of marker_id, severity, or text"

    _, markers = parse_collect(code)
    matches = find_markers(markers, marker_id, severity, text)

    criteria = ", ".join(
        "%s=%r" % (k, v)
        for k, v in (("marker_id", marker_id), ("severity", severity),
                     ("text", text))
        if v is not None)

    assert matches, \
        "Expected a marker matching %s; markers emitted were:\n%s" % (
            criteria, _format_markers(markers))

    if count is not None:
        assert len(matches) == count, \
            "Expected %d markers matching %s, got %d:\n%s" % (
                count, criteria, len(matches), _format_markers(matches))

    return matches[0]


def assert_no_marker(code: str, marker_id: Optional[str] = None,
                     severity: Optional[str] = None,
                     text: Optional[str] = None):
    """
    Assert no marker matching the given criteria was emitted.

    Args:
        code: PSS source code
        marker_id: Marker code that must be absent
        severity: Severity that must be absent
        text: Message substring that must be absent

    Raises:
        AssertionError if a matching marker was emitted
    """
    assert marker_id is not None or severity is not None or text is not None, \
        "assert_no_marker requires at least one of marker_id, severity, or text"

    _, markers = parse_collect(code)
    matches = find_markers(markers, marker_id, severity, text)

    assert not matches, \
        "Expected no matching marker, but got:\n" + _format_markers(matches)


def assert_parse_ok_with_warning(code: str, marker_id: Optional[str] = None,
                                 text: Optional[str] = None) -> Any:
    """
    Assert the code parses and links successfully *and* emits a warning.

    This is the shape PSS 3.1 deprecations take: the construct remains legal,
    so the parse must succeed, but a diagnostic must accompany it. Asserting
    only one half of that would let either regression through.

    Args:
        code: PSS source code
        marker_id: Expected warning code (e.g. "PSS101")
        text: Substring expected in the warning message

    Returns:
        The linked symbol scope root

    Raises:
        AssertionError if parsing fails, or if no matching warning was emitted
    """
    root, markers = parse_collect(code)

    errors = [m for m in markers if m.get("severity") == "error"]
    assert root is not None and not errors, \
        "Expected a successful parse, but got errors:\n" + _format_markers(errors)

    matches = find_markers(markers, marker_id, "warning", text)
    assert matches, \
        "Parse succeeded but expected warning was not emitted; markers were:\n" \
        + _format_markers(markers)

    return root


# =============================================================================
# Code Generators for Testing
# =============================================================================

def generate_actions(num_actions: int, with_fields: bool = False, 
                     with_constraints: bool = False) -> str:
    """
    Generate PSS code with multiple actions
    
    Args:
        num_actions: Number of actions to generate
        with_fields: If True, add random fields to actions
        with_constraints: If True, add constraints to actions
        
    Returns:
        PSS source code string
    """
    lines = ["component pss_top {"]
    
    for i in range(num_actions):
        lines.append(f"    action A{i} {{")
        
        if with_fields:
            lines.append(f"        rand int x{i};")
            lines.append(f"        rand int y{i};")
        
        if with_constraints:
            lines.append(f"        constraint {{")
            lines.append(f"            x{i} > 0;")
            lines.append(f"            y{i} < 100;")
            lines.append(f"        }}")
        
        lines.append(f"    }}")
    
    lines.append("}")
    return "\n".join(lines)


def generate_components(num_components: int, nested: bool = False) -> str:
    """
    Generate PSS code with multiple components
    
    Args:
        num_components: Number of components to generate
        nested: If True, create nested component hierarchy
        
    Returns:
        PSS source code string
    """
    if not nested:
        lines = []
        for i in range(num_components):
            lines.append(f"component C{i} {{")
            lines.append(f"}}")
        return "\n".join(lines)
    else:
        # Create nested hierarchy
        lines = []
        for i in range(num_components):
            lines.append(f"{'    ' * i}component C{i} {{")
        for i in range(num_components - 1, -1, -1):
            lines.append(f"{'    ' * i}}}")
        return "\n".join(lines)


def generate_constraints(num_constraints: int, field_prefix: str = "x") -> str:
    """
    Generate constraint block with multiple constraints
    
    Args:
        num_constraints: Number of constraints to generate
        field_prefix: Prefix for field names
        
    Returns:
        PSS constraint block string
    """
    lines = ["constraint {"]
    for i in range(num_constraints):
        lines.append(f"    {field_prefix}{i} > 0;")
        lines.append(f"    {field_prefix}{i} < 1000;")
    lines.append("}")
    return "\n".join(lines)


def generate_register_model(num_registers: int, with_fields: int = 2) -> str:
    """
    Generate register model with multiple registers
    
    Args:
        num_registers: Number of registers to generate
        with_fields: Number of fields per register
        
    Returns:
        PSS source code string
    """
    lines = ["component pss_top {"]
    
    for i in range(num_registers):
        lines.append(f"    register reg{i} {{")
        for j in range(with_fields):
            lines.append(f"        field bits[31:0] field{j};")
        lines.append(f"    }}")
    
    lines.append("}")
    return "\n".join(lines)


def generate_struct_hierarchy(depth: int) -> str:
    """
    Generate nested struct hierarchy
    
    Args:
        depth: Nesting depth
        
    Returns:
        PSS source code string
    """
    lines = []
    for i in range(depth):
        indent = "    " * i
        lines.append(f"{indent}struct S{i} {{")
        if i < depth - 1:
            lines.append(f"{indent}    S{i+1} nested;")
        else:
            lines.append(f"{indent}    int value;")
    
    for i in range(depth - 1, -1, -1):
        indent = "    " * i
        lines.append(f"{indent}}}")
    
    return "\n".join(lines)


def generate_activity_parallel(num_actions: int) -> str:
    """
    Generate parallel activity with multiple action invocations
    
    Args:
        num_actions: Number of actions in parallel block
        
    Returns:
        PSS activity code string
    """
    lines = ["activity {", "    parallel {"]
    for i in range(num_actions):
        lines.append(f"        do A{i};")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)


# =============================================================================
# Comparison Helpers
# =============================================================================

def compare_ast_structures(node1, node2) -> bool:
    """
    Compare two AST nodes for structural equality
    
    Args:
        node1: First AST node
        node2: Second AST node
        
    Returns:
        True if structures match, False otherwise
    """
    # TODO: Implement when AST comparison is needed
    return True


# =============================================================================
# Debug Helpers
# =============================================================================

def print_symbol_tree(scope, indent: int = 0):
    """
    Print symbol tree for debugging
    
    Args:
        scope: Symbol scope to print
        indent: Indentation level
    """
    if scope is None:
        return
    
    prefix = "  " * indent
    name = scope.getName() if hasattr(scope, 'getName') else str(scope)
    print(f"{prefix}{name}")
    
    # Print children
    if hasattr(scope, 'children'):
        for child in scope.children():
            print_symbol_tree(child, indent + 1)


def dump_scope_symbols(scope):
    """
    Dump all symbols in scope for debugging
    
    Args:
        scope: Symbol scope to dump
    """
    if scope is None:
        print("Scope is None")
        return
    
    print(f"Scope: {scope.getName() if hasattr(scope, 'getName') else 'unknown'}")
    
    util = SymbolScopeUtil(scope)
    for child in scope.children():
        name = child.getName() if hasattr(child, 'getName') else str(child)
        print(f"  - {name}")
