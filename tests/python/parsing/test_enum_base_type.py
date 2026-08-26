"""
`enum <name> : <data_type> { ... }` -- BNF line 3286.

Only an enum that has a base type may be a member of a packed struct
(21.13.1), which is what makes the clause load-bearing rather than cosmetic.
"""
from pssparser import ast

from ..test_helpers import assert_parse_ok


def _enum_base_types(root):
    """name -> base-type node (or None) for every enum in the tree."""
    found = {}

    class V(ast.VisitorBase):
        def visitEnumDecl(self, i):
            found[i.getName().getId()] = i.getBase_type()

    root.accept(V())
    return found


def test_enum_with_base_type_parses():
    root = assert_parse_ok(
        """
        package t {
            import std_pkg::*;
            enum mode_e : bit[4] { IDLE = 0, RUN = 1, HALT = 2 };
            enum kind_e : int { A = 0, B = 1 };
            enum plain_e { X = 0, Y = 1 };
            struct s : packed_s<LITTLE_ENDIAN> { mode_e mode; bit[28] rsvd_4; }
        }
        """
    )
    assert root is not None


def test_base_type_is_carried_on_the_declaration():
    root = assert_parse_ok(
        """
        package t {
            enum mode_e : bit[4] { IDLE = 0, RUN = 1 };
            enum plain_e { X = 0, Y = 1 };
        }
        """
    )
    bases = _enum_base_types(root)

    assert bases["mode_e"] is not None
    assert isinstance(bases["mode_e"], ast.DataTypeInt)
    # An enum without the clause must not acquire one.
    assert bases["plain_e"] is None


def test_enum_with_user_defined_base_type():
    root = assert_parse_ok(
        """
        package t {
            typedef bit[8] byte_t;
            enum small_e : byte_t { A = 0, B = 1 };
        }
        """
    )
    bases = _enum_base_types(root)
    assert bases["small_e"] is not None
