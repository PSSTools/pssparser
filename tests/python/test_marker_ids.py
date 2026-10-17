"""
Pins the core marker-ID catalogue and the message-to-ID mapping.

Most core markers originate in C++ without an ID; the ID comes from matching
the message text against the ``patterns`` declared on each ``MarkerDef`` --
in C++, by the marker collector, from the generated catalogue
(lint-core-plan C7.3), and in Python by ``_assign_core_code``, the same table.
That makes the C++ message strings part of the contract, with nothing in the
build to enforce it -- hence this file.  The core-emitted lint carries its ID
from where C++ emits it, and no pattern may claim its messages.

Two kinds of coverage here:

1. **Mapping** -- representative message text for each ID maps to that ID, and
   nothing shadows anything else. A new pattern added in the wrong place will
   fail here rather than silently mis-labelling diagnostics.
2. **Discoverability** -- every declared ID is reachable through
   ``--list-markers`` and ``--describe``, which is the acceptance criterion for
   the PSS 3.1 marker allocation (plan item P0-T2).
"""
import io
import re

import pytest

from pssparser.checkers.core_checker import CoreChecker
from pssparser.cli.commands import _assign_core_code
from pssparser.lint.catalog import CORE_EMITTED


# Representative message text for each core ID. For PSS100+ these are the
# messages the not-yet-written C++ code is *required* to emit -- keeping them
# here means the ID mapping is settled before the emitting code is written.
REPRESENTATIVE_MESSAGES = [
    # PSSP000 is set on the C++ marker directly; the pattern is the fallback
    # for a message that reaches Python without its code.
    ("PSSP000", "internal error in resolving references: vector::_M_range_check; "
               "please report this"),
    ("PSSP000", "internal error while building the AST: boom; please report this"),
    ("PSS001", "expected ';' before '}'"),
    ("PSS001", "unexpected end of input; possible missing closing '}'"),
    ("PSS001", "unknown exec-block kind 'wibble'"),
    ("PSS001",
     "unexpected low bound '1' in an integer width; only '0' is permitted, "
     "as in 'bit[7:0]'"),
    ("PSS002", "unknown type 'Foo'"),
    ("PSS002", "unknown type 'Nope' in 'p::q'"),
    ("PSS002", "unknown identifier 'bar'"),
    ("PSS002", "unknown method 'baz' on built-in type"),
    ("PSS003", "duplicate declaration of 'a'"),
    ("PSS003", "duplicate symbol declaration"),
    ("PSS003", "duplicate parameter name 'p'"),
    ("PSS003", "duplicate variable declaration x, previously declared"),
    ("PSS004", "failed to resolve ref-path a.b.c"),
    ("PSS004", "root ref-path element x is not a composite scope"),
    ("PSS002", "'comp' is only valid in an action declared in a component, "
               "and 'AB' is declared outside one"),
    ("PSS002", "'prev' is only valid in a state type or its extension, and "
               "cannot be reached as a member of 'i'"),
    ("PSS003", "duplicate declaration of 'uid': every action has a built-in "
               "'uid'"),
    # Extension merging (symbol-resolution 7.1).
    ("PSS003", "duplicate declaration of 'a' in an extension of 'S': its "
               "initial definition already declares it (17.2.3)"),
    ("PSS003", "duplicate declaration of 'b' in an extension of 'S': another "
               "extension in package 'p' already declares it (17.2.3)"),
    ("PSS003", "duplicate declaration of enum item 'B' in 'e1': an enum item "
               "must be unique across the enum and all its extensions (7.5.1)"),
    ("PSS005", "cannot extend unknown type 'Foo'"),
    ("PSS005", "cannot extend unknown enum 'MyEnum'"),
    ("PSS005", "cannot extend unknown type 'a' in 'C'; an extension inside a "
               "component may extend only a type the component declares (17.3)"),
    ("PSS005", "cannot extend 'x': it is not an extendable type"),
    ("PSS005", "cannot extend 's' as an enum: it is not an enum type"),
    ("PSS019", "cannot import function 'f' here: it is declared in component "
               "'base_c', and may be imported only in that component type "
               "(20.4.1)"),
    ("PSS019", "cannot import function 'f': it is declared in template "
               "component 't_c' (20.4.1)"),
    ("PSS019", "cannot import function 'f': it is an instance function of "
               "component 'pss_top', and instance functions cannot be "
               "imported (20.4)"),
    ("PSS019", "cannot import function 's': a component function must be "
               "declared 'static' to be imported; instance functions cannot "
               "be imported (20.4)"),
    ("PSS040", "'fld' is an instance member of 'sub_c' and cannot be "
               "referenced through the type; only types, static constants, "
               "static functions and enum items can (18.3)"),
    ("PSS040", "cannot reference instance member 'fld' from static function "
               "'st_f': a static function has no component instance (20.2)"),
    ("PSS041", "cannot reach static member 'st' of 'my_ip_c' through "
               "'comp'; name it without 'comp.', as 'st' (9.1.4.1 f)"),
    ("PSS041", "cannot reach static member 'SK' of 'sub_c' through 'comp'; "
               "name it through the type instead, as 'sub_c::SK' (9.1.4.1 f)"),
    ("PSS042", "'x' was left unbound by pssparser, although the model "
               "declares it: a pssparser defect, please report it"),
    ("PSS043", "package alias 'X' is already declared in this scope; two "
               "aliases in one scope shall not share a name (18.1.4)"),
    ("PSS043", "package alias 'foo' has the same name as a package declared "
               "in package 'P'; rename the alias (18.1.4)"),
    ("PSS047", "template parameter 'N' expects a value, but 'my_s' is a type"),
    ("PSS047", "template parameter 'N' expects a value, but the argument "
               "supplied is a type"),
    ("PSS047", "template parameter 'T' expects a type, but the argument "
               "supplied is a value"),
    ("PSS048", "struct literal names 'a' more than once (4.8.4)"),
    ("PSS048", "struct literal names 'c1', which is not a data attribute of "
               "'S1' (4.8.4)"),
    ("PSS049", "bind names 'x', which is not a pool (12.3)"),
    ("PSS049", "bind names 'x', which is not a component instance of 'C' "
               "(12.3)"),
    ("PSS049", "bind names 'x', which is not an action type of 'C' (12.3)"),
    ("PSS049", "bind names 'x', which is not an input, output or "
               "resource-claim field of 'A' (12.3)"),
    ("PSS050", "cross 'X' names 'f', which is not a coverpoint or a data "
               "field (15.4)"),
    ("PSS050", "bins 'b' names 'a', which is not its own coverpoint 'c' "
               "(15.3.3.3)"),
    ("PSS050", "bins 'b' names 'Y', which is not its own cross 'X' (15.4.3)"),
    ("PSS002", "covergroup 'cg_t' has no port named 'x'"),
    ("PSS051", "'b' is declared by an extension of 'S' in package 'p', which "
               "is not visible here (17.2.3); add 'import p::*;'"),
    ("PSS051", "'b' is declared by an extension of 'S' in package 'p' and "
               "package 'q', none of which is visible here (17.2.3); add "
               "'import p::*;'"),
    ("PSS051", "'B' is an item an extension of 'E' in package 'p' adds, which "
               "is not visible here (17.2.3); add 'import p::*;'"),
    ("PSS052", "'import lib::s;' names 's', which package 'p' already "
               "declares; an explicit import shall not name a declaration of "
               "the importing namespace (18.1.3)"),
    ("PSS052", "'s' is already imported explicitly in this scope, by 'import "
               "lib1::s;'; the same name shall not be imported explicitly "
               "from two packages (18.1.3)"),
    ("PSS054", "compile assert failed: too wide"),
    ("PSS054", "compile assert failed for 'S<64>': too wide"),
    ("PSS055", "compile if condition cannot be evaluated at compile time: "
               "'X>1'. Compile-time expressions may reference only types and "
               "constants declared in this source unit or in a "
               "previously-processed one (PSS 3.1 19.1.2)"),
    ("PSS055", "compile assert condition cannot be evaluated for 'S<4>': a "
               "compile-time expression may reference only constants and "
               "template parameters (19.4)"),
    ("PSS056", "'t' is not a generic type, so it takes no template arguments"),
    ("PSS057", "cannot extend a type declared inside a template instance: "
               "not supported by pssparser (17.2.6)"),
    ("PSS058", "'extend action' names 'M', which is a monitor; "
               "write 'extend monitor M' (17.2)"),
    ("PSS058", "'extend monitor' names 'A', which is an action; "
               "write 'extend action A' (17.2)"),
    ("PSS059", "cyclic inheritance: 'A' -> 'B' -> 'A'"),
    ("PSS060", "'array' takes 2 template arguments, but 3 are given"),
    ("PSS060", "'list' takes 1 template argument, but 2 are given"),
    ("PSS060", "no value supplied for template parameter 'N', and it has "
               "no default"),
    ("PSS060", "no type supplied for template parameter 'T', and it has "
               "no default"),
    ("PSS060", "template type 'P' requires a template argument list"),
    ("PSS061", "template parameter 'T' requires an argument of type category "
               "'struct', but the argument 'c' is of category 'component'"),
    ("PSS061", "template parameter 'T' is restricted to 'base_s' and its "
               "subtypes, but the argument 'x_s' does not derive from "
               "'base_s'"),
    ("PSS062", "recursive specialization of 'S' exceeded the maximum depth "
               "of 32: each step specializes on a larger argument than the "
               "last, so the chain does not terminate"),
    ("PSS063", "cannot override action 'A': no action of that name is "
               "declared in a base component of 'C'"),
    ("PSS063", "cannot override template action 'A'"),
    ("PSS063", "action 'A' must be declared 'override': 'C' declares it as "
               "an override action"),
    ("PSS064", "symbol 's1' activates itself: s1 -> s2 -> s1 (11.7)"),
    ("PSS006", "argument 1 of 's' is a value, but parameter 'h' is a handle "
               "of action 'A'"),
    ("PSS006", "argument 1 of 't' is an action handle, but parameter 'n' is "
               "numeric"),
    ("PSS002", "'tx' is a component instance, not a type or package; did you "
               "mean 'tx_c'?"),
    ("PSS018", "'s' is a symbol, not an action handle; a symbol takes no "
               "'with' constraints (11.7)"),
    ("PSS002", "cannot resolve 'y': the enclosing scope is unknown"),
    ("PSS003", "duplicate declaration of 'attr' in an extension of an "
               "instance of 'domain_s': the type already declares it (17.2.3)"),
    ("PSS017", "ambiguous reference to 'b': extensions of 'S' in package 'p' "
               "and package 'q' each declare it, and each package is imported "
               "here (17.2.3); import only one"),
    ("PSS006", "call to 'g' expects 1 argument, got 3"),
    ("PSS006", "call to 'g' expects 1 to 2 arguments, got 0"),
    ("PSS006", "call to 'g' expects at least 1 argument, got 0"),
    ("PSS006", "no overload of 'g' accepts 3 arguments"),
    # PSS006 covers the whole "call does not match the callee's parameters"
    # family -- count, argument type, and calling something that is not a
    # function. Both message spellings reach it: checkCallArity's for an
    # ordinary call, TaskCheckCallArgs's for a built-in method signature.
    ("PSS006", "too few arguments to 'f': expected 2, got 1"),
    ("PSS006", "too many arguments to 'f': expected at most 2, got 3"),
    ("PSS006", "argument 1 of 'g' is a string, but parameter 'a' is numeric"),
    ("PSS006", "'f' is not a function"),
    ("PSS007", "'f' returns void, so 'return' cannot take a value"),
    ("PSS008", "'f' is declared pure, so it cannot return void"),
    ("PSS009", "declarations of 'f' disagree about the return type"),
    ("PSS010", "no field 'chan_en' in register value type 'csr_s'"),
    ("PSS011", "invalid digit 'G' in based literal"),
    ("PSS012", "field 'mode' of packed struct 'ctrl_s' is enum 'mode_e', "
               "which has no base type; declare it as 'enum mode_e : bit[N]'"),
    ("PSS012", "field 'h' of packed struct 's' is a chandle; use "
               "sized_addr_handle_s<SZ> for an address"),
    ("PSS012", "field 'f' of packed struct 's' is a string, which cannot be packed"),
    ("PSS013", "type extension of packed struct 's' adds field 'b'; an "
               "extension of a packed struct may not add fields"),
    ("PSS014", "reg_c value type is struct 'cfg_s', which is not packed"),
    ("PSS014", "reg_c width SZ = 32 is smaller than its value type 'd_s' "
               "(40 bits)"),
    ("PSS015", "sizeof_s argument is a string, which has no packed size"),
    ("PSS017", "ambiguous reference to 's': more than one wildcard import "
               "provides it, so none does (18.1.3); qualify the name"),
    ("PSS018", "'x' is not an action handle, and cannot be traversed; only "
               "a handle, or a data field declared with the 'action' "
               "modifier, can be"),
    ("PSS018", "'A' is a type, not an action handle; traverse it by type "
               "with 'do A'"),
    ("PSS018", "'L1' is an activity label, not an action handle, and cannot "
               "be traversed"),
    ("PSS018", "'fc' is a fixed constraint, which always holds and cannot be "
               "traversed; declare it as a generic constraint, "
               "'constraint fc() { ... }', to apply it here"),
    ("PSS018", "'S' is not an action type, and cannot be traversed"),
    ("PSS002", "'A' has no member named 'nosuch'"),
    ("PSS002", "base type 'B' has no member named 'c'"),
    ("PSS002", "'super' is only valid inside a type that has a base type, "
               "and 'S' has none"),
    ("PSS002", "'super;' is only valid inside a type that has a base type, "
               "and 'S' has none"),
    ("PSS002", "'super' is only valid inside a type: an action, component, "
               "struct or other type body"),
    ("PSS100", "annotation is not attached to a model element"),
    ("PSS102", "annotation initializer for 'owner' is not a constant expression"),
    ("PSS105", "illegal 'mutable' qualifier: not permitted on a rand field"),
    ("PSS106", "exec block tag is not permitted on 'body' exec blocks"),
    ("PSS107", "member selection is not permitted on a slice of 'arr'"),
    # PSS108/PSS109 -- the exact text emitted for the `{{` collision (D3.3).
    # The hint is a *suffix* on both, which keeps each pattern anchored on its
    # distinguishing prefix rather than on the shared tail.
    ("PSS108",
     "unterminated mustache expression; if '{{' was intended as literal text, "
     "separate the braces ('{ {') -- triple-quoted strings have no escape mechanism"),
    ("PSS109",
     "malformed mustache expression: unexpected ','; if '{{' was intended as "
     "literal text, separate the braces ('{ {')"),
    ("PSS110", "unterminated template directive"),
    ("PSS110", "unterminated template comment"),
    ("PSS110", "unclosed template block at end of string"),
    ("PSS110", "malformed template directive: expected ';' after assignment"),
    ("PSS111", "template block close with no open block"),
    ("PSS111", "'else' with no preceding 'if'"),
    ("PSS112",
     "template assignment target 'a' is not declared within this template string"),
    ("PSS113", "template expression is not of scalar type"),
    ("PSS114", "call to non-pure function 'f' in a template string"),
    ("PSS115",
     "template string with non-constant elements is not a constant expression"),
    ("PSSP101", "`override` is accepted but not represented in the AST"),
    ("PSSP101",
     "`randomize` is accepted but not represented in the AST: "
     "the `with` constraints are dropped"),
    ("PSS002", "'x' is used before its declaration on line 4; in a block, a "
               "name is visible only after it is declared"),
    ("PSS118", "constant 'C' is used in the initializer of 'A' before its "
               "declaration on line 4; declare it first (18.2)"),
    ("PSS118", "enum item 'E_X' is used in the initializer of 'A' before its "
               "declaration in a file given later; declare it first (18.2)"),
    ("PSS118", "constant 'A' is used in the initializer of 'A', which is "
               "itself (18.2)"),
    ("PSS118", "package-level constant 'A' may reference only package-level "
               "constants; 'K' is declared in type 'C' (18.2)"),
    ("PSS121", "constant 'C' cannot be assigned: a constant cannot appear on "
               "the left of an assignment (LRM 7.1)"),
    ("PSS121", "an element or member of constant 'TBL' cannot be assigned: a "
               "constant's elements are constants too (LRM 7.1)"),
    ("PSS121", "parameter 'x' is const, so its value cannot be changed in the "
               "function body (LRM 20.2.3)"),
    ("PSS121", "an element or member of const parameter 's' cannot be changed "
               "in the function body (LRM 20.2.3)"),
    ("PSS006", "argument 1 of 'g' is constant 'C', so parameter 's' must be "
               "declared const (LRM 20.2.3)"),
    ("PSS122", "a sub-string of 's' on the left of an assignment: the "
               "sub-string operator shall not be used there (LRM 7.6.2)"),
    ("PSS123", "foreach index variable 'i' is read-only and cannot be changed "
               "in the foreach body (LRM 20.7.8 g)"),
    ("PSS123", "foreach iterator variable 'e' is read-only and cannot be "
               "changed in the foreach body (LRM 20.7.8 g)"),
    ("PSS123", "'w' is the collection this foreach iterates, so it cannot be "
               "changed in the foreach body (LRM 20.7.8 g)"),
    ("PSS123", "'l' is the collection this foreach iterates, so 'push_back()' "
               "cannot change it in the foreach body (LRM 20.7.8 g)"),
    ("PSS124", "'break' may only appear within a loop statement: repeat, "
               "while or foreach (LRM 20.7.11 b)"),
    ("PSS124", "'continue' may only appear within a loop statement: repeat, "
               "while or foreach (LRM 20.7.11 b)"),
    ("PSS125", "a match statement may have at most one default branch; this "
               "is a second one (LRM 20.7.10 f)"),
    ("PSS007", "an exec block returns void, so 'return' cannot take a value "
               "(LRM 20.7.5, ruling R21)"),
    ("PSS126", "a cast to struct p_s: a casting type shall be a numeric, "
               "Boolean, enumeration or reference type (LRM 7.12.1)"),
    ("PSS126", "a cast from chandle: only a numeric, Boolean or enumeration "
               "value, or a reference, can be cast (LRM 7.12)"),
    ("PSS127", "the left side of 'in' shall not be an aggregate literal "
               "(LRM 8.5.9.1)"),
    ("PSS127", "the left side of 'in' is struct p_s, not a scalar, so the right "
               "side shall be a collection, not a range list (LRM 8.5.9.1)"),
    ("PSS128", "'==' does not apply to an array of components or actions: only "
               "[], size(), foreach and 'in' do (LRM 7.9.2)"),
    ("PSS128", "an array of components or actions cannot be assigned: only [], "
               "size(), foreach and 'in' apply to one (LRM 7.9.2)"),
    ("PSS006", "argument 1 of 'sum' is an array of 3 elements, but parameter "
               "'v' is an array of 2 (LRM 8.3)"),
    ("PSS129", "function 'g' returns component type 'sub_c' without 'ref': a "
               "function shall not (LRM 20.2.2)"),
    ("PSS129", "parameter 'b' of 'f' has flow object type 'b_s' without 'ref': "
               "a function shall not (LRM 20.2.2)"),
    ("PSS130", "enum item 'ORANGE' is used where no enumeration type is "
               "expected (7.5.1 i, 8.4.3; ruling R22); qualify it as "
               "'color_e::ORANGE'"),
    ("PSS130", "enum item 'RED' is used where 'mode_e' is expected, but it is "
               "an item of 'color_e' (7.5.1 i, 8.4.3; ruling R22); qualify it "
               "as 'color_e::RED'"),
    ("PSS131", "operator '<' takes numeric operands, not bool (LRM 8.4 Table "
               "10, 8.5.2)"),
    ("PSS131", "operator '&=' takes integer operands, not bool (LRM 8.3 Table 9)"),
    ("PSS131", "a chandle can be compared only with a chandle or the literal 0, "
               "not int (LRM 7.7)"),
    ("PSS132", "the condition of 'if' shall be of Boolean type, not int "
               "(LRM 20.7.9)"),
    ("PSS133", "null cannot be assigned to int: only a reference takes null "
               "(LRM 8.3)"),
    ("PSS134", "enum item 'B' has the value 1, as 'A' does: each enum item "
               "shall have a distinct value (LRM 7.5.1 e)"),
    ("PSS134", "enum item 'A' has the value -1, which is not a value of the "
               "base type bit[4] (LRM 7.5.1 c)"),
    ("PSS134", "enum item 'B' has no value of its own, and the item before it "
               "has the greatest value of the base type bit[2] (LRM 7.5.1 c)"),
    ("PSS134", "the base type of enum 'h_e' shall not have a value domain "
               "(LRM 7.5.1)"),
    ("PSS135", "'v' is a variable of enum 'n_e', which has no items in its "
               "declaration or any extension (LRM 7.5.1 j)"),
    ("PSS009", "declarations of 'f' disagree about whether parameter 1 ('x') "
               "is const (LRM 20.2.3 c)"),
    ("PSS009", "declarations of 'f' disagree about the platform qualifier: one "
               "is target, the other solve (LRM 20.3.1)"),
    ("PSS009", "'der_c::f' and the 'base_c::f' it overrides disagree about the "
               "number of parameters (1 and 3)"),
    ("PSS009", "static function 'der_c::f' cannot shadow the instance function "
               "'base_c::f' (LRM 20.2)"),
    ("PSS009", "'der_c::f' is pure but overrides the non-pure 'base_c::f' "
               "(LRM 20.2.6)"),
    ("PSS136", "parameter 'rest' of 'f' is varargs, which only a core-library "
               "function may have (LRM 20.2.5, ruling R23)"),
    ("PSS137", "parameter 'v' of imported function 'put' has type bit[65], "
               "which an import cannot take (LRM 20.4.1 c)"),
    ("PSS137", "imported function 'f' returns float, which an import cannot "
               "(LRM 20.4.1 c)"),
    ("PSS137", "parameter 'p' of exported function 'sf' is a struct, so it "
               "shall be declared const (LRM 20.4.2.1 g)"),
    ("PSS138", "integer width 0 is not positive (LRM 7.2.1 c, ruling R19)"),
    ("PSS139", "division by a constant zero is illegal (LRM 8.5.1)"),
    ("PSS139", "a shift by the constant -1: the right operand shall be "
               "non-negative (LRM 8.5.7)"),
    ("PSS140", "channel 'ch' cannot hold string (LRM 21.9.1 a)"),
    ("PSS140", "channel 'ch' has DEPTH 0: it shall be positive (LRM 21.9.1 b)"),
    ("PSS141", "register 'X' is in 'pss_top', which is not a register group "
               "(LRM 21.14.1)"),
    ("PSS141", "'reg_group_c' cannot be extended (LRM 21.14.2)"),
    ("PSS142", "rand field 'h' is of type chandle, which is not randomizable "
               "(LRM 7.1)"),
    ("PSS142", "a randomize target of type chandle, which is not randomizable "
               "(LRM 7.1, 13.4.6, ruling R18)"),
    ("PSS143", "'yield' may only be used in target code; solve function 'f' is "
               "solve code (LRM 20.7.14 a, ruling R20)"),
    ("PSS144", "'write32' is a target function and cannot be called from solve "
               "function 'initialize', which is solve code (LRM 20.2.1.3)"),
    ("PSS145", "exec body is not valid in a component: it is valid in actions "
               "(LRM 20.1.2)"),
    ("PSS145", "a target-template exec block cannot be init_down, a solve exec "
               "kind (LRM 20.5)"),
    ("PSS146", "a compile if condition may not reference 'LOC', a member of type "
               "'pss_top' (LRM 19.1.3 b)"),
    ("PSS147", "'b' is private to 'p_s' and cannot be reached from here "
               "(LRM 17.4 b)"),
    ("PSS142", "rand field 'm' is a map, which is not randomizable (LRM 7.1)"),
    ("PSS148", "'in' cannot be applied directly to a map: use its keys() or "
               "values() (LRM 7.9.4)"),
    ("PSS148", "'s' is a set, which cannot be indexed or sliced (LRM 8.4 Table "
               "10, 7.9.5)"),
    ("PSS148", "'pop_back' changes its collection, so it shall not be used in a "
               "constraint or activity (LRM 7.9)"),
    ("PSS149", "'r' is a reference field, which a struct or object cannot "
               "declare (LRM 7.10 a)"),
    ("PSS149", "'q' is declared instance, but its type is not a component "
               "reference (LRM 9.1.5.3 a)"),
    ("PSS149", "parameter 'c' of 'f' is a reference, which cannot be const "
               "(LRM 20.2.3 b)"),
]


#: The core-emitted lint (lint/catalog.py), whose code C++ sets where it emits
#: them (lint-core-plan C7.3): no pattern may claim their messages.
#: tests/python/lintcore/test_catalog.py checks the codes on the markers.
CORE_LINT_MESSAGES = [
    ("LINT401", "'A' is read as the enum item mode_e::A, which hides the "
               "field 'A' (18.3 a); qualify one of them"),
    ("LINT402", "'import lib::*;' follows a declaration; imports shall come "
               "first in a package, a component, an extension or a file "
               "(18.1.3)"),
    ("LINT501", "reg_c width SZ = 96 has no primitive access function; use 8, "
               "16, 32 or 64 bits"),
    ("LINT403", "unknown annotation type 'desc_s'; annotation disregarded"),
    ("LINT601", "'compile if' branch without enclosing braces is deprecated"),
    ("LINT602", "traversal of dynamic constraint 'dc' is deprecated (13.1.1); "
               "declare it as a generic constraint, 'constraint dc() { ... }'"),
    ("LINT404", "constant 'W' is used in a type width before its declaration "
               "on line 5; declare it first (18.2)"),
    ("LINT301", "exported function 'bump' is not static; exporting a "
               "component's instance function is an extension to 20.4.2"),
]


@pytest.mark.parametrize("expected_id,message", REPRESENTATIVE_MESSAGES)
def test_message_maps_to_expected_id(expected_id, message):
    assigned = _assign_core_code({"message": message})
    assert assigned.get("code") == expected_id, \
        "message %r mapped to %r, expected %r" % (
            message, assigned.get("code"), expected_id)


@pytest.mark.parametrize("message", [m for _, m in CORE_LINT_MESSAGES])
def test_no_pattern_claims_core_lint(message):
    assert "code" not in _assign_core_code({"message": message})


def test_the_core_assigns_the_same_codes(factory):
    """The core's marker collector gives a marker without a code the code of
    the catalogue's patterns (C7.3): the same table, so the same answers."""
    engine = factory.mkLintEngine()
    messages = [m for _, m in REPRESENTATIVE_MESSAGES + CORE_LINT_MESSAGES]
    messages += ["some entirely novel diagnostic", ""]
    got = {m: engine.core_code(m) for m in messages}
    want = {m: _assign_core_code({"message": m}).get("code", "") for m in messages}
    assert got == want


def test_unmatched_message_gets_no_code():
    """A message no pattern claims must stay uncoded, not fall through to one."""
    assigned = _assign_core_code({"message": "some entirely novel diagnostic"})
    assert "code" not in assigned


def test_existing_code_is_not_overwritten():
    """Checker-produced markers already carry a code; leave it alone."""
    assigned = _assign_core_code({"message": "unknown type 'Foo'", "code": "PSC001"})
    assert assigned["code"] == "PSC001"


# -- catalogue integrity ----------------------------------------------------

def test_marker_ids_are_unique():
    ids = [m.id for m in CoreChecker.marker_defs]
    assert len(ids) == len(set(ids))


def test_marker_ids_are_in_ascending_order():
    """Patterns are tried in declaration order, so keep that order legible.

    PSS rows come first, then the PSSP rows, then the core-emitted LINT
    rules appended from ``pssparser.lint.catalog``; each run is ascending.
    A code that moved keeps a retired row at its old position, which is
    where its patterns are tried (``_build_core_patterns``).
    """
    from pssparser.checkers.taxonomy import split_code

    ids = [m.id for m in CoreChecker.marker_defs]
    namespaces = [split_code(i)[0] for i in ids]
    runs = [ns for k, ns in enumerate(namespaces) if k == 0 or ns != namespaces[k - 1]]
    assert runs == ["PSS", "PSSP", "LINT"]
    for ns in runs:
        nums = [split_code(i)[1] for i in ids if split_code(i)[0] == ns]
        assert nums == sorted(nums), ns


#: PSS020-PSS028: syntax-classification sub-band (PSS029, the --max-errors
#: cutoff, is now PSSP007; it is set by MarkerCollector::marker in C++). These IDs
#: arrive on the marker directly from C++, not via message-pattern matching,
#: so `patterns` is deliberately empty and there is nothing to add to
#: REPRESENTATIVE_MESSAGES for them -- see SYNTAX_BAND_SAMPLES and
#: test_syntax_band_ids_are_reachable below instead.
#: PSS023 is reserved, not assigned (see core_checker.py). PSS027 is the
#: lexer's, and became reachable with A6.
_SYNTAX_BAND = {"PSS0%02d" % n for n in range(20, 29)} | {"PSSP007"}

#: The tool's own diagnostics: PSS030-PSS039 (now retired rows) and every
#: PSSP code but PSSP000, PSSP007 and PSSP101. Like the syntax band these carry their
#: code directly rather than acquiring one by message matching -- but for the
#: opposite reason. Syntax-band markers come from C++ with a code already
#: attached; these are constructed in *Python* (CheckerManager's discovery
#: pass, the config layer) and never pass through a parser at all.
#:
#: A pattern on one of these would be actively harmful: `_build_core_patterns`
#: exists to recover an ID for C++ markers that have none, so a pattern here
#: could claim an unrelated parser message and report it as, say, a failed
#: extension load.  The exceptions come from C++: PSSP000 (internal error,
#: code set directly, pattern as a fallback), PSSP007 (counted with the
#: syntax band above) and PSSP101 (the builder; pattern-matched).
_TOOLING_BAND = {"PSS0%02d" % n for n in range(30, 40)} | {
    m.id for m in CoreChecker.marker_defs
    if m.id.startswith("PSSP") and m.id not in ("PSSP000", "PSSP007", "PSSP101")
}

#: Codes that are never emitted: retired (moved or withdrawn) and reserved.
_NOT_EMITTED = {m.id for m in CoreChecker.marker_defs if not m.emittable}

#: IDs whose code is set at construction rather than recovered from the
#: message text, or that are never emitted. Neither `patterns` nor a
#: REPRESENTATIVE_MESSAGES entry applies to them.
_DIRECT_CODE_BANDS = _SYNTAX_BAND | _TOOLING_BAND | _NOT_EMITTED | {
    md.id for md in CORE_EMITTED}


def test_every_core_marker_declares_patterns():
    """A core marker with no pattern can never be assigned to a diagnostic."""
    missing = [
        m.id for m in CoreChecker.marker_defs
        if not m.patterns and m.id not in _DIRECT_CODE_BANDS
    ]
    assert not missing, "core markers with no message patterns: %s" % missing


def test_every_marker_has_a_representative_message():
    """Every declared ID must be exercised by the mapping test above."""
    covered = {mid for mid, _ in REPRESENTATIVE_MESSAGES + CORE_LINT_MESSAGES}         | _DIRECT_CODE_BANDS
    declared = {m.id for m in CoreChecker.marker_defs}
    assert declared - covered == set(), \
        "IDs with no representative message: %s" % sorted(declared - covered)


def test_tooling_band_markers_declare_no_patterns():
    """A tooling-band pattern could shadow a real parser diagnostic."""
    offenders = [
        m.id for m in CoreChecker.marker_defs
        if m.id in _TOOLING_BAND and m.patterns
    ]
    assert not offenders, "tooling-band markers with unnecessary patterns: %s" % offenders


def test_assign_core_code_never_fires_for_the_tooling_band():
    """These markers are built with their code; _assign_core_code must not
    be able to attach one to an unrelated message."""
    for marker_id in sorted(_TOOLING_BAND):
        assigned = _assign_core_code({"message": "some entirely novel diagnostic"})
        assert assigned.get("code") != marker_id


def test_the_tooling_band_is_declared_where_the_manager_emits_it():
    """Every code CheckerManager can emit must be a declared MarkerDef.

    The manager builds these dicts by hand, so nothing else would catch a
    typo'd or undeclared code until a user hit the failure path.
    """
    import re
    from pathlib import Path

    declared = {m.id for m in CoreChecker.marker_defs}
    source = Path(__file__).resolve().parents[2] / "python" / "pssparser" / "checkers" / "manager.py"
    emitted = set(re.findall(r'self\._issue\(\s*"((?:PSSP|PSS|LINT)\d+)"', source.read_text()))

    assert emitted, "no _issue() calls found; has manager.py been restructured?"
    assert emitted <= declared, \
        "manager emits undeclared codes: %s" % sorted(emitted - declared)
    assert emitted <= _TOOLING_BAND, \
        "manager emits codes outside the tooling band: %s" % sorted(emitted - _TOOLING_BAND)


def test_syntax_band_markers_declare_no_patterns():
    """The inverse of test_every_core_marker_declares_patterns: a syntax-band
    marker's code comes from C++, so a pattern here would be dead weight that
    could silently shadow a real (checker-produced) diagnostic."""
    offenders = [
        m.id for m in CoreChecker.marker_defs
        if m.id in _SYNTAX_BAND and m.patterns
    ]
    assert not offenders, "syntax-band markers with unnecessary patterns: %s" % offenders


def test_assign_core_code_never_fires_for_the_syntax_band():
    """_assign_core_code only fills in a missing code; a syntax-band marker
    must always already carry one by the time Python sees it."""
    for marker_id in sorted(_SYNTAX_BAND - {"PSS023"}):
        assigned = _assign_core_code({"message": "some entirely novel diagnostic"})
        assert assigned.get("code") != marker_id


#: One real snippet per reachable syntax-band ID, parsed through the actual
#: C++ parser (not the message-pattern table above -- there is none for these
#: IDs). PSS023 is reserved/unreachable (see core_checker.py) and is
#: deliberately absent here. The third element is the --max-errors value
#: to apply before parsing (None = library default, unlimited) -- only
#: PSSP007 needs one, since it is the cap-cutoff marker itself.
SYNTAX_BAND_SAMPLES = [
    ("PSS020", "struct S { int x }", None),
    ("PSS021", "struct S { int x; ", None),
    ("PSS022", "struct S { int ; }", None),
    ("PSS024", "class C { }", None),
    ("PSS025", "struct S { int x; * }", None),
    ("PSS026", "enum E { struct };", None),
    # Lexical, not syntactic: the string never closes, so the lexer is the
    # one that reports it.
    ("PSS027", 'struct S { string a = "abc; }', None),
    ("PSS028", "struct S { 123 x; }", None),
    (
        "PSSP007",
        "\n".join("struct S%d { int ; }" % i for i in range(5)),
        2,
    ),
]


@pytest.mark.parametrize("expected_id,source,max_errors", SYNTAX_BAND_SAMPLES)
def test_syntax_band_ids_are_reachable(expected_id, source, max_errors):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent))
    from test_helpers import parse_collect

    try:
        _root, markers = parse_collect(source, max_errors=max_errors)
    except Exception as exc:
        markers = getattr(exc, "markers", [])
    codes = [m.get("code") for m in markers]
    assert expected_id in codes, \
        "parsing %r produced codes %r, expected %r among them" % (
            source, codes, expected_id)


def test_syntax_band_samples_cover_every_reachable_id():
    covered = {mid for mid, _, _ in SYNTAX_BAND_SAMPLES}
    reachable = _SYNTAX_BAND - {"PSS023", "PSS027"}
    assert reachable - covered == set(), \
        "reachable syntax-band IDs with no sample: %s" % sorted(reachable - covered)


def test_every_reachable_syntax_band_id_has_a_corpus_case():
    """Exit criterion for E-3: every PSS020-PSS028 ID that can actually be
    emitted (excludes the reserved PSS023/PSS027) has >= 1 corpus case,
    queried the same way test_corpus.py does -- over both roots, since the L1
    cases now live in error-suite/cases/ (error-suite design §3.4)."""
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent / "errors"))
    from corpus_loader import collect_cases

    roots = [None, _Path(__file__).parents[2] / "error-suite" / "cases"]
    cases = []
    for root in roots:
        if root is None:
            cases += collect_cases()
        elif root.is_dir():
            cases += collect_cases(root)
    ids_with_cases = {c.id for c in cases if c.id in _SYNTAX_BAND}
    reachable = _SYNTAX_BAND - {"PSS023", "PSS027"}
    assert reachable - ids_with_cases == set(), \
        "reachable syntax-band IDs with no corpus case: %s" % sorted(
            reachable - ids_with_cases)


def test_all_patterns_compile():
    for mdef in CoreChecker.marker_defs:
        for pat in mdef.patterns:
            re.compile(pat, re.IGNORECASE)


def test_severities_are_valid():
    valid = {"error", "warning", "info", "hint"}
    for mdef in CoreChecker.marker_defs:
        assert mdef.severity in valid, \
            "%s has invalid severity %r" % (mdef.id, mdef.severity)


def test_pss31_band_is_reserved_for_31_diagnostics():
    """PSS100-PSS199 is the PSS 3.1 band; PSS001-PSS099 the general one."""
    pss31 = [m.id for m in CoreChecker.marker_defs
             if m.id.startswith("PSS") and not m.id.startswith("PSSP")
             and 100 <= int(m.id[3:]) <= 199]
    # PSS103 is retired (see core_checker.py): §7.13b is enforced by the
    # grammar, so no linker check can emit it. The gap is deliberate -- the ID
    # must not be reused. PSS101, 104, 116, 117, 119 and 120 are retired
    # rows too: those warnings moved to LINT/PSSP (lint-framework D-1, D-6).
    assert pss31 == ["PSS100", "PSS101", "PSS102", "PSS103",
                     "PSS104", "PSS105", "PSS106", "PSS107",
                     "PSS108", "PSS109", "PSS110", "PSS111", "PSS112",
                     "PSS113", "PSS114", "PSS115", "PSS116", "PSS117",
                     "PSS118", "PSS119", "PSS120", "PSS121", "PSS122",
                     "PSS123", "PSS124", "PSS125", "PSS126", "PSS127",
                     "PSS128", "PSS129", "PSS130", "PSS131", "PSS132",
                     "PSS133", "PSS134", "PSS135", "PSS136", "PSS137",
                     "PSS138", "PSS139", "PSS140", "PSS141", "PSS142",
                     "PSS143", "PSS144", "PSS145", "PSS146", "PSS147",
                     "PSS148", "PSS149"]


def test_every_active_pss_marker_is_an_error():
    """PSS means an LRM violation; a warning is lint (LINT) or about the
    tool (PSSP). The retired rows point at where each warning went."""
    offenders = [
        m.id for m in CoreChecker.marker_defs
        if m.id.startswith("PSS") and not m.id.startswith("PSSP")
        and m.emittable and m.severity != "error"
    ]
    assert offenders == []


def test_moved_codes_point_at_a_declared_successor():
    by_id = {m.id: m for m in CoreChecker.marker_defs}
    for m in CoreChecker.marker_defs:
        if m.status == "retired" and m.replaced_by:
            target = by_id[m.replaced_by[0]]
            assert m.id in target.aliases, (m.id, target.id)


def test_pssp_markers_are_tool_tier():
    assert all(
        m.tier == "tool" for m in CoreChecker.marker_defs
        if m.id.startswith("PSSP")
    )


# -- CLI discoverability (P0-T2 acceptance criterion) ------------------------

def _manager():
    from pssparser.checkers import CheckerManager
    manager = CheckerManager()
    manager.discover()
    return manager


def test_list_markers_shows_every_core_id():
    from pssparser.cli.checker_cmds import cmd_list_markers

    out = io.StringIO()
    assert cmd_list_markers(_manager(), stdout=out) == 0
    text = out.getvalue()

    for mdef in CoreChecker.marker_defs:
        assert mdef.id in text, "%s missing from --list-markers" % mdef.id


@pytest.mark.parametrize("marker_id", [m.id for m in CoreChecker.marker_defs])
def test_describe_returns_detail_for_every_core_id(marker_id):
    from pssparser.cli.checker_cmds import cmd_describe

    out = io.StringIO()
    err = io.StringIO()
    assert cmd_describe(_manager(), marker_id, stdout=out, stderr=err) == 0, \
        err.getvalue()
    text = out.getvalue()
    assert marker_id in text
    assert len(text.strip()) > len(marker_id) + 20, \
        "--describe %s produced no substantive text" % marker_id


def test_describe_rejects_unknown_id():
    from pssparser.cli.checker_cmds import cmd_describe

    out = io.StringIO()
    err = io.StringIO()
    assert cmd_describe(_manager(), "PSS999", stdout=out, stderr=err) == 2
    assert "unknown marker" in err.getvalue()
