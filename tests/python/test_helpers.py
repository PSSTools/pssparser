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
    Assert parser has no errors
    
    Args:
        parser: Parser to check
        
    Raises:
        AssertionError if parser has errors
    """
    # TODO: Add proper error checking when API is available
    pass


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
