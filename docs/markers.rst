Marker Reference
================

Every diagnostic the built-in core checker can emit, generated from
``CoreChecker.marker_defs`` by ``scripts/gen_marker_docs.py`` -- do not edit
this file by hand, it will be overwritten.

``PSS001``-``PSS099`` is the general band, ``PSS020``-``PSS028`` its syntax
sub-band, and ``PSS100``-``PSS199`` is the PSS 3.1 language-rule band.
``PSS023`` and ``PSS027`` are reserved within the syntax sub-band and
deliberately have no entry below -- see ``PSS022``'s detail and
``core_checker.py``'s syntax-band comment (U-9) respectively for why. Query
the same information from the command line with ``--list-markers`` and
``--describe <ID>``.

PSS000
------

**Severity:** error

Internal error

pssparser reached a state it believed could not happen.  This is a defect in pssparser, not necessarily in the model, and it should be reported together with the input that triggers it.  The message names the phase or link pass that failed:

* ``internal error in resolving references: ...``
* ``internal error while building the AST: ...``

Results for the rest of the model are incomplete: the pass that failed stopped, and the passes after it did not run.  The command-line tool exits with status 3 when an internal error is reported.

PSS001
------

**Severity:** error

Syntax error

The parser encountered a token it did not expect.  Messages include patterns such as:

* ``expected ';' before '}'``
* ``unexpected end of input; possible missing closing '}'``
* ``unexpected '<token>' in this context``
* ``expected identifier before '<token>'``
* ``syntax error at '<token>'``

Check that the surrounding PSS syntax is well-formed.

PSS002
------

**Severity:** error

Unknown symbol reference

The linker could not resolve a named type, identifier, or method.  Messages include patterns such as:

* ``unknown type 'Foo'``
* ``unknown type 'Foo' in 'pkg'`` (the name is not in the qualifying package or scope)
* ``unknown identifier 'bar'``
* ``unknown method 'baz' on built-in type``
* ``unknown function 'f': an import of this form needs a separate declaration of the function (20.4.1)``
* ``'pkg' has no member named 'thing'``
* ``Failed to find elem 'thing'``
* ``'this' is only valid inside a type: ...`` (``this`` in a package-level function)
* ``'super' is only valid inside a type that has a base type, and 'S' has none`` (also ``'super;'``)
* ``'comp' is only valid in an action declared in a component, and 'AB' is declared outside one``
* ``'prev' is only valid in a state type or its extension, and cannot be reached as a member of 'i'``
* ``base type 'B' has no member named 'x'`` (``super.x``)

The last two are the same diagnosis reached through a qualified and an unqualified path respectively.

Ensure the symbol is declared in one of the source files passed to pssparser, or that the correct package is imported.  When a close match exists, a ``did you mean '...'?`` suggestion is appended.

PSS003
------

**Severity:** error

Duplicate symbol declaration

A symbol with this name is already declared in the same scope.  Messages include patterns such as:

* ``duplicate declaration of 'Foo'``
* ``duplicate variable declaration bar``
* ``duplicate parameter name 'p'``
* ``duplicate symbol declaration``
* ``duplicate parameter name 'a'``
* ``function 'f' is already defined``
* ``function 'f' cannot be both defined and imported``
* ``function 'f' is already imported``
* ``duplicate declaration of 'a' in an extension of 'S': its initial definition already declares it (17.2.3)``
* ``duplicate declaration of enum item 'B' in 'e': an enum item must be unique across the enum and all its extensions (7.5.1)``

Rename one of the declarations to resolve the conflict.

Note that ``duplicate declaration of '...'`` is currently emitted as a *warning* while the others are errors.

PSS004
------

**Severity:** error

Symbol or ref-path resolution failure

A symbol or reference path could not be resolved during linking.  Messages include patterns such as:

* ``failed to resolve ref-path <path>``
* ``failed to resolve symbol <name>``
* ``root ref-path element <x> is not a composite scope``

Check that all referenced symbols are declared and that composite-type fields are used correctly.

PSS005
------

**Severity:** error

Cannot extend unknown type or enum

An ``extend`` declaration targets a type or enum that does not exist, or a name that is not a type of the kind extended.  Messages include patterns such as:

* ``cannot extend unknown type 'Foo'``
* ``cannot extend unknown enum 'MyEnum'``
* ``cannot extend unknown type 'a' in 'C'; an extension inside a component may extend only a type the component declares (17.3)``
* ``cannot extend 'x': it is not an extendable type``
* ``cannot extend 's' as an enum: it is not an enum type``

Ensure the base type is declared before or alongside the extend block.

PSS006
------

**Severity:** error

Call does not match the callee's parameters

A function call supplies more or fewer arguments than the callee declares, names something that is not a function, or the callee's parameter list is itself malformed.  Messages include patterns such as:

* ``too few arguments to 'f': expected 2, got 1``
* ``too many arguments to 'f': expected 1, got 2``
* ``'x' is not a function``
* ``'size' is a method; call it as 'size()'``
* ``'v' is not a symbol; only a symbol can be called in an activity``
* ``parameter 'b' has no default, but follows 'a' which does``
* ``argument 1 of 'f' is a string, but parameter 'a' is numeric``

Argument types are compared only by broad category -- numeric, string, composite.  Widths, signedness and struct subtyping are deliberately not judged.

Parameters with a default may be omitted, which is why the bound is reported as ``at least``/``at most`` when the two differ.  A ``type... args`` parameter removes the upper bound entirely.

PSS007
------

**Severity:** error

Return type used inconsistently

A ``return`` supplies a value from a ``void`` function, omits one where a return type is declared, or the result of a ``void`` call is used as a value.  Messages include patterns such as:

* ``'f' returns void, so 'return' cannot take a value``
* ``'f' has a return type, so 'return' must supply a value``
* ``'f' returns void, so its result cannot be used as a value``

The last of these is LRM 20.5: a void function "may only be called as a standalone procedural statement".  The converse -- calling a non-void function as a statement and discarding the result -- is explicitly legal and is not reported.

Taking a member of a call result counts as using it, so ``f().x`` on a void ``f`` is reported here rather than as a resolution failure.  A *scalar* return is not: ``f().x`` on an int-returning ``f`` gets the same PSS004 message a scalar variable would.

Whether a non-void function returns on *every* path is not checked.

PSS008
------

**Severity:** error

Function qualifier is not allowed here

A ``pure`` or parameter-direction qualifier is used where the LRM does not allow it.  Messages include patterns such as:

* ``parameter 'a' of 'f' is declared output, so 'f' may only be imported, not defined in PSS``
* ``'f' is declared pure, so it cannot return void``
* ``'f' is declared pure, so parameter 'a' cannot be output``

Direction modifiers (LRM 20.2.2, 20.3.2) mark a function as importable only; a function carrying one on any of its declarations may not also have a PSS body.  Functions built into an implementation, such as the core library, are exempt.

``pure`` (LRM 20.2.6) asserts that the result depends only on the arguments and that evaluation has no side effects, so a pure function can be neither ``void`` nor take an ``output``/``inout`` parameter.

The ``const`` parameter qualifier (LRM 20.2.3) is parsed and discarded rather than checked -- no AST node records it.

PSS009
------

**Severity:** error

Declarations of one function disagree

A function may be declared more than once -- a prototype and a definition, a prototype and an ``import`` -- and LRM 20.2 requires every declaration to give the same signature.  Messages include patterns such as:

* ``declarations of 'f' disagree about the return type``
* ``declarations of 'f' disagree about the return type: one returns void and the other does not``
* ``declarations of 'f' disagree about the number of parameters (1 and 2)``
* ``declarations of 'f' disagree about the type of parameter 1 ('a')``
* ``declarations of 'f' disagree about the direction of parameter 1 ('a')``
* ``declarations of 'f' disagree about what kind of parameter 1 ('a') is``
* ``declarations of 'f' disagree about whether parameter 2 ('args') is varargs``
* ``declarations of 'f' disagree about the default value of parameter 2 ('y')``

Reported once per function, against the declaration the rest of the tool treats as authoritative: a definition's prototype where there is one, otherwise the first.

The last of these is LRM 3.1 20.2.4 c: a redeclaration may repeat a default, "but this value shall be equal".  The values are compared after folding; a default that does not fold to a constant is not reported.  (PSS 3.0 forbade repeating a default at all.)  A default given by only one declaration is in effect for all of them.

Only a *certain* difference is reported.  A ``typedef`` alias, an integer width that will not fold to a constant, a default width against a written one, and a type name that did not resolve are all cases where the two declarations may well agree, and none of them is reported.

Three things are deliberately **not** compared. Parameter *names*, because PSS calls are positional and nothing requires a redeclaration to reuse them.  A ``pure`` qualifier, because LRM 20.2.6 b permits omitting it in a definition whose declaration carries it.  The ``const`` qualifier, which LRM 20.2.3 c does make part of the signature -- but it is parsed and discarded, so there is nothing to compare.

A *static* function shadowed in a derived component may differ freely (LRM 20.2) and is not reported.  An *instance* function shadowed in a derived component must match, and that is not checked.

PSS010
------

**Severity:** error

Bad field name in a masked register write

``write_field`` / ``write_fields`` / ``write_masked`` (LRM 21.14.1) name a *declared field* of the register's value type.  The string spelling is forced by the signature ``write_field(string name, bit[SZ] val)`` and does not make the name data: 21.14.1 restricts it to a string **literal** precisely so a tool can resolve it at compile time.  Messages include patterns such as:

* ``no field 'chan_en' in register value type 'csr_s'; did you mean 'ch_en'?``
* ``write_field: field 'sub' of 'agg_s' has a composite type; field-wise register access applies to scalar fields only``
* ``write_field: the field name must be a string literal``
* ``write_field: field name 'a.b' must not be a hierarchical reference``
* ``write_fields: duplicate field name 'prio'``
* ``write_fields: 2 field name(s) but 1 value(s)``
* ``write_masked: no field 'nosuch' in register value type 'csr_s'``
* ``write_field: this register's value type is not a struct, so it has no named fields``

A duplicate name matters more than it looks: the plural form writes its fields in a *single* read-modify-write, so naming one twice does not write it twice -- one of the two values is simply lost.

Which **bits** a resolved field occupies is deliberately not decided here.  ``packed_s<>`` layout is a target representation -- backends order it oppositely on purpose -- so the compiler folds the mask.  This checks *which field*; the compiler answers *which bits*.

PSS011
------

**Severity:** error

Digit out of range for a based literal's radix

A based literal (LRM B.19, e.g. ``'hFF``, ``8'b1010``) contains a digit that is not valid for its radix -- for example a hex literal spelled with a letter past ``f``/``F``. The lexer accepts any alphanumeric run after the radix character so a typo still lexes as one literal token (rather than a lexical error splitting the trailing characters into an unrelated token); this check then validates the digits against the radix. Only the first invalid digit is reported. Message: ``invalid digit '<c>' in based literal``.

PSS012
------

**Severity:** error

Packed struct field has a type a packed struct cannot hold

A packed struct -- any struct derived, directly or indirectly, from ``packed_s`` -- may only have fields of numeric types, ``bool``, enumerated types that have a base type, packed struct types, or fixed-size arrays of these (LRM 21.13.1). Anything else has no defined bit layout. Messages take the form ``field '<f>' of packed struct '<s>' is <what>; <how to fix it>``, for example:

* ``field 'mode' of packed struct 'ctrl_s' is enum 'mode_e', which has no base type; declare it as 'enum mode_e : bit[N]'``
* ``field 'h' of packed struct 'desc_s' is a chandle; use sized_addr_handle_s<SZ> for an address``
* ``field 'q' of packed struct 's' is struct 'q_s', which is not packed; derive it from packed_s<>``
* ``field 'l' of packed struct 's' is a list; use a fixed-size array, 'T name[N]'``
* ``field 's' of packed struct 'd' is a string, which cannot be packed``

A width-less enum is not 32 bits wide in a packed struct: it is not allowed there at all. A flow or resource object that inherits from a packed struct is not itself packed (LRM 17.1). ``static const`` members are not part of the layout and are not checked. A generic packed struct is checked per specialization.

PSS013
------

**Severity:** error

Type extension adds a field to a packed struct

LRM 21.13.1: "Type extensions of packed structs shall not add new fields." A packed struct's layout is fixed by its declaration; an ``extend`` elsewhere must not change it. Constraints, exec blocks and ``static const`` members may still be added. Message: ``type extension of packed struct '<s>' adds field '<f>'; an extension of a packed struct may not add fields``.

PSS014
------

**Severity:** error

Register value type has no size, or is wider than the register

``reg_c<R, ACC, SZ>`` (LRM 21.14.1) lays a value of type ``R`` over a register ``SZ`` bits wide. ``R`` must have a known packed size -- a packed struct, or another packable type such as ``bit[N]``, ``int[32]`` or an enum with a base type -- and ``SZ``, when given, must be at least ``sizeof_s<R>::nbits``. (Omitting ``SZ`` gives ``8*sizeof_s<R>::nbytes``, which always fits.) Messages include:

* ``reg_c value type is struct 'cfg_s', which is not packed; derive it from packed_s<>``
* ``reg_c value type is enum 'mode_e', which has no base type; ...``
* ``reg_c width SZ = 32 is smaller than its value type 'desc_s' (40 bits)``

Reported where the register type is used (``reg_c<...>`` as a field type or a base type), not in the core library.

PSS015
------

**Severity:** error

sizeof_s of a type that has no packed size

LRM 21.13.2.1: ``sizeof_s<>`` "shall not be parameterized with types other than numeric types, Booleans, enumerated types that have a base type, packed structs, and arrays thereof." Such a specialization has no ``nbits`` or ``nbytes`` value. Message: ``sizeof_s argument is <what>, which has no packed size``, or ``sizeof_s argument is <what>; <how to fix it>``. A packed struct with a bad member is reported at the member (PSS012), not here.

PSS016
------

**Severity:** warning

Register width has no primitive access function

LRM 21.14.5a translates register reads and writes into the primitive ``read8/16/32/64`` and ``write8/16/32/64`` functions (21.13.9), chosen by the register's size. A register ``SZ`` bits wide, where ``SZ`` is not 8, 16, 32 or 64, has no such function, so its access cannot be translated as the spec describes. Not a "shall" in the spec, so a warning. A packed struct of any size is legal on its own -- a 96-bit DMA descriptor, say; this is only about using one as a register value type. Message: ``reg_c width SZ = 96 has no primitive access function; use 8, 16, 32 or 64 bits``. For a register whose value type is narrower than a primitive, give ``SZ`` explicitly (``reg_c<my12_s, READWRITE, 16>``).

PSS017
------

**Severity:** error

Ambiguous name: more than one import provides it

LRM 18.1.3: when two imports of the same kind make the same name visible, and they name different declarations, the name is not imported at all. An explicit import (``import p::s;``) takes precedence over a wildcard import (``import p::*;``), so only imports of the same kind can conflict. Two imports that reach the same declaration do not conflict.  Message: ``ambiguous reference to 's': more than one wildcard import provides it, so none does (18.1.3); qualify the name``. Qualify the name (``lib1::s``) or import it explicitly.

PSS018
------

**Severity:** error

Traversal of something that is not an action

An action traversal statement names something that cannot be traversed.  LRM 11.3.1: the identifier "names a unique action handle or variable in the context of the containing action type or activity scope"; a variable may be a data field declared with the ``action`` modifier, which is randomized with no execution (Example 173).  A generic constraint (13.4.11), a deprecated ``dynamic`` constraint (see PSS117) and a symbol may also be traversed.  Messages include:

* ``'x' is not an action handle, and cannot be traversed; only a handle, or a data field declared with the 'action' modifier, can be``
* ``'A' is a type, not an action handle; traverse it by type with 'do A'``
* ``'L1' is an activity label, not an action handle, and cannot be traversed``
* ``'c' is a fixed constraint, which always holds and cannot be traversed; ...`` -- write it as a generic constraint, ``constraint c() { ... }``
* ``'S' is not an action type, and cannot be traversed`` (``do S`` on a struct or component)

A name that is not declared at all is PSS002.

PSS019
------

**Severity:** error

Function cannot be imported here

An ``import ... function`` names a function that the LRM does not allow to be imported from where the import is written.  Messages include patterns such as:

* ``cannot import function 'f' here: it is declared in component 'base_c', and may be imported only in that component type (20.4.1)``
* ``cannot import function 'f': it is declared in template component 't_c' (20.4.1)``
* ``cannot import function 'f': it is an instance function of component 'c', and instance functions cannot be imported (20.4)``
* ``cannot import function 'f': a component function must be declared 'static' to be imported; instance functions cannot be imported (20.4)``

LRM 20.4.1: a static function declared in a component can be imported only in the scope of that same component type -- not in a derived component, an unrelated one, or a package -- and a function declared in a template component cannot be imported at all.  Declare the function where it is imported, or move the import next to the declaration.  A function declared in a package can be imported anywhere it is visible.

LRM 20.4: an instance (non-static) function cannot be imported.  In a component, the prototype form of the import must say ``static`` (20.4.1.1 b.1), so ``import C function void f(int a);`` there is reported whether or not ``f`` is declared ``static`` elsewhere; the name form (``import C function f;``) is reported when no declaration of ``f`` says ``static``.

PSS020
------

**Severity:** error

Expected specific punctuation before this token

The parser reached a point where only one or two specific punctuation tokens could legally continue the construct, and the next token was not one of them. Messages include patterns such as:

* ``expected ';' before '<token>'``
* ``expected '{' or ':' before '<token>'``
* ``expected '{' or ':' before 'extends'; use ':' for inheritance, not 'extends'``

Insert the missing punctuation, or (for the last case) replace ``extends`` with ``:``.

PSS021
------

**Severity:** error

Unexpected end of input

The file ended while a scope (``{ ... }``) was still open.

When the still-open scope is a ``component`` or ``struct`` declared directly (not several rules deeper, e.g. mid ``exec`` body), the marker is reported **at the opening ``{``** of that declaration, named by kind and identifier, with the end-of-file position attached as a related location:

* ``unclosed '{' for component '<name>'``
* ``unclosed '{' for struct '<name>'``

Otherwise -- a deeper truncation, or any other brace-opening construct (``enum``, ``constraint``, an ``exec`` body, ...) -- the marker falls back to the generic end-of-file message, reported at the end of file itself:

* ``unexpected end of input; missing closing '}'``

For the fallback case, count braces from the point the parser last made progress; the true cause is often several lines above the file's last line, not at it.

PSS022
------

**Severity:** error

Expected an identifier before this token

The grammar requires an identifier at this position and the next token is not one. Reached via either of ANTLR's two recovery strategies for the same situation: single-token-insertion (offending token already in the follow set, e.g. ``;``, ``{``, ``=``) or a full mismatched-input exception whose expecting-set is exactly identifier-shaped (``{ID, ESCAPED_ID}``, optionally with a leading ``'::'``) -- which is how a real PSS keyword used where an identifier belongs (``struct``, ``return``, ...) lands here too. There is no reachable keyword sub-case distinct from this one -- **PSS023 is reserved, not assigned**.

Messages:

* ``expected identifier before '<token>'``
* ``'this' is a keyword and cannot be used as a declared name`` -- the one keyword the lexer returns as an identifier, so the grammar accepts it and the declaration is rejected afterwards

PSS024
------

**Severity:** error

Unexpected token in this context

A general ``mismatched input`` case that PSS020, PSS021, and PSS022 do not cover more specifically: the token is not one of the (possibly several) tokens that could legally appear here. Messages include patterns such as:

* ``unexpected '<token>' in this context`` (the expecting set was too large to usefully quote)
* ``unexpected '<token>' expecting {<alternatives>}`` (the expecting set was small enough to show)

PSS025
------

**Severity:** error

Unexpected punctuation in this context

A single punctuation token appears where nothing could legally follow.

Message: ``unexpected '<token>' in this context``

The same wording as PSS024's first pattern; the two differ only in which ANTLR exception produced them (``extraneous input`` here, ``mismatched input`` there).

PSS026
------

**Severity:** error

Unexpected token in this context (non-punctuation)

As PSS025, but the extraneous token is not a single punctuation character -- a keyword, a multi-character operator, or a literal. Only called a "keyword" in the message when it actually looks like one (starts with a letter or ``_``); anything else, such as a numeric literal, gets the plain PSS025-style wording while keeping this ID. Messages include patterns such as:

* ``unexpected keyword '<token>' in this context``
* ``unexpected '<token>' in this context`` (non-keyword-looking offender, e.g. ``123``)

PSS027
------

**Severity:** error

Lexical error: the text could not be made into a token

The lexer, not the parser, could not read this. It is reported where the unreadable run *starts* -- the opening quote or ``/*`` -- rather than wherever the parser later tripped over what was left, which is usually a line or two further on and about the wrong thing entirely.

Messages include patterns such as:

* ``unterminated string literal``
* ``unterminated triple-quoted string literal``
* ``unterminated block comment``
* ``unexpected character '<c>'``

The parse error that a lexical defect provokes immediately afterwards is suppressed: an unterminated string swallows the rest of its line, so what follows not parsing is the same defect, not a second one.

PSS028
------

**Severity:** error

Syntax error (unclassified alternative)

ANTLR could not decide among the grammar's alternatives at this point (a ``no viable alternative`` exception) and no more specific rewrite applies.

Message: ``syntax error at '<token>'``

The message does not say what was expected; work outward from the enclosing construct to find the mistake.

PSS029
------

**Severity:** error

Too many errors; stopped reporting further errors

``--max-errors`` (default 20; ``0`` disables the cap) was reached for this file. Only error-severity markers count against it -- warnings and hints never trigger it, and a clean file never sees it. Emitted once, at the location of the error that pushed the count over the limit; every further error in that file is dropped, not merely hidden, so re-running with a higher (or ``0``) ``--max-errors`` is the only way to see what comes after it.

Message: ``too many errors (<N>); stopped reporting further errors for this file``

PSS030
------

**Severity:** warning

A checker extension could not be loaded

An entry point in the ``pssparser.extensions`` (or legacy ``pssparser.checkers``) group failed to load. The usual causes are an import error inside the extension, an exception raised from its ``register()`` function, or a module that exposes neither ``register()`` nor the ``CHECKERS`` shorthand.

The run continues: a third-party extension is code you did not write, and one broken package must not stop the rest of the registry from loading. The consequence is that the rules that extension contributes did **not** run, so a clean result is not evidence of clean source.

Use ``--list-extensions`` to see what did load, and ``--no-extensions`` (or ``PSSPARSER_NO_EXTENSIONS=1``) to confirm the behaviour is the extension's and not pssparser's. In CI, ``-Werror=PSS030`` makes a failed extension fatal, which is usually what you want.

PSS031
------

**Severity:** warning

Entry-point key disagrees with the checker's declared name

A legacy ``pssparser.checkers`` entry point is keyed under one name while the class it names declares another in its ``name`` attribute.

The class is authoritative -- it is the name the checker reports itself under and the name ``--checker`` and ``--no-checker`` select -- so the checker is registered under the declared name and the entry-point key is ignored. Rename the key to match; while they disagree, a command line written against the key silently selects nothing.

PSS032
------

**Severity:** warning

Extension requires a newer checker API than this build provides

The extension declared ``requires_api = N`` (as a module level ``REQUIRES_API`` or on the registry inside ``register()``) and ``N`` is greater than this build's ``pssparser.checkers.API_VERSION``.

The extension is not loaded, deliberately: refusing here produces one clear message, where loading it anyway produces an ``AttributeError`` from inside a checker halfway through a run. Upgrade pssparser, or install a build of the extension made for this API version.

PSS033
------

**Severity:** error

Two checkers declare the same marker ID

Marker IDs are globally unique across the core and every installed extension. Two rules wearing one ID make ``--describe``, ``-Werror=ID`` and every per-ID severity override ambiguous, so the collision is an error rather than a warning.

The checker that lost the collision is not registered; everything else, including the rest of its extension, still loads. The message names both contributors. The fix belongs in the extension: pick an unused prefix -- three letters plus three digits is the convention, and the ``PSS`` prefix is reserved for the built-in core checker.

PSS040
------

**Severity:** error

Instance member used without an instance

A reference reaches a field or function that belongs to an instance of a type from a place that has no instance to take it from.  Messages include patterns such as:

* ``'fld' is an instance member of 'sub_c' and cannot be referenced through the type; only types, static constants, static functions and enum items can (18.3)``
* ``cannot reference instance member 'fld' from static function 'st_f': a static function has no component instance (20.2)``

LRM 18.3: a type's namespace holds types, static constants, static functions and enum items, so ``T::m`` cannot name an ordinary field or an instance function; reach it through an instance with ``.`` instead.  A reference written inside ``T``, a subtype of ``T`` or an extension of either is not reported, since a base-qualified call there has an instance to use.  A ``const`` field is treated as a constant.

LRM 20.2: a static component function is not associated with an instance, so its body cannot read the component's non-static fields or call its instance functions.  Make the member static, pass the value in as a parameter, or drop ``static`` from the function.

PSS041
------

**Severity:** error

Static member used through 'comp'

An action reaches a static function or static constant of a component through its ``comp`` handle.  Messages include patterns such as:

* ``cannot reach static member 'f' of 'my_c' through 'comp'; name it without 'comp.', as 'f' (9.1.4.1 f)``
* ``cannot reach static member 'K' of 'sub_c' through 'comp'; name it through the type instead, as 'sub_c::K' (9.1.4.1 f)``

LRM 9.1.4.1 f: "It shall be illegal to access static component members using the comp handle."  ``comp`` is an instance; a static member belongs to the component type (20.2.1.1 c).  A member of the action's own component is found by its plain name, since the action is declared inside that component or an extension of it; a member of a sub-component is named through its type, ``sub_c::f``.  Reported for every path that starts at ``comp``, including ``comp.sub.f()``.

PSS042
------

**Severity:** error

Reference left unbound (pssparser defect)

The linker finished without binding a name, although the model declares something of that name, and without saying why.  This is a defect in pssparser, not necessarily in the model: please report it together with the input.  Message:

* ``'x' was left unbound by pssparser, although the model declares it: a pssparser defect, please report it``

Reported by the completeness check that runs after linking (symbol-resolution plan 3.5), so that a consumer is never handed a reference with no target in silence.  It is reported only on a model with no other error; with one, an unbound name is far more likely a consequence of that error.  A name that nothing in the model declares is PSS002 instead.  Some constructs are not checked yet: covergroup bodies and port maps, pool and activity binds, scheduling constraints, instance overrides, struct-literal member names, and the parameters of a generic constraint.

PSS043
------

**Severity:** error

Illegal package alias declaration

LRM 18.1.4 restricts the name of a package alias (``import pkg1::a::b as p1;``).  Messages:

* ``package alias 'X' is already declared in this scope; two aliases in one scope shall not share a name (18.1.4)``
* ``package alias 'foo' has the same name as a package declared in package 'P'; rename the alias (18.1.4)``

Two aliases in one lexical scope -- one ``package`` statement, component declaration or extension, or one file's global scope -- shall not have the same name; the same name in two statements of one package is legal.  An alias shall not take the name of a package declared in the same namespace in this source unit or an earlier one (Example 260).  A package of that name added in a later source unit is legal, and from then on a reference finds the package rather than the alias (18.3 c.1 before c.2.i).

PSS044
------

**Severity:** warning

Enum item hides a declaration of the same name

Where an expression's expected type is an enumeration type (8.4.3), an unqualified name is looked up among that enum's items before any scope (18.3 a).  A field, variable or parameter of the same name is then hidden, which is legal but rarely intended.  Message:

* ``'A' is read as the enum item mode_e::A, which hides the field 'A' (18.3 a); qualify one of them``

Write ``mode_e::A`` for the item, or rename the field.

PSS045
------

**Severity:** error

Ambiguous enum item in a comparison

In ``a == b`` or ``a != b`` each side's type is the other side's expected type, so an unqualified name on either side may be an item of the other side's enum.  When both sides are bare names and each could be read that way, there is no telling which was meant.  Message:

* ``ambiguous comparison of 'A' and 'B': either 'A' is e2::A or 'B' is e1::B; qualify the enum item (8.4.3, 18.3 a)``

Qualify the item, as ``e1::B``.

PSS046
------

**Severity:** warning

Enum item used where its enumeration type is not expected

An enum item belongs to its enumeration type's scope, not to the scope that declares the enum (7.5 g).  Unqualified, it is found only where the expression's expected type is that enumeration type (7.5 i, 8.4.3, 18.3 a): an assignment or initializer, a call argument, a ``return``, the other side of ``==``/``!=``, the values of ``in``, a cast to the enum, and the arms of ``?:``.  pssparser still accepts an item declared in an enclosing scope, or in a package a wildcard import names, when the name means nothing else there, and warns; this becomes an error in a later release.  A declaration of the same name further out is what the name means, and no longer the item.  Messages:

* ``enum item 'ORANGE' is used where no enumeration type is expected (7.5 i, 8.4.3); qualify it as 'color_e::ORANGE'``
* ``enum item 'RED' is used where 'mode_e' is expected, but it is an item of 'color_e' (7.5 i, 8.4.3); qualify it as 'color_e::RED'``

Qualify the item.  LRM Example 37: ``print_num((int)ORANGE)`` is an error, because the cast's type is ``int``.

PSS047
------

**Severity:** error

Template argument of the wrong kind

A template parameter is either a value parameter or a type parameter (10.3), and its argument has to be of the same kind.  A name spells a type and a constant alike, so ``S<X>`` is decided by what ``X`` names: for a value parameter, ``X`` is looked up as a value -- an enum item of the parameter's enumeration type first (18.3 a), then the usual scopes -- and a type found there is reported.  Messages:

* ``template parameter 'N' expects a value, but 'my_s' is a type``
* ``template parameter 'N' expects a value, but the argument supplied is a type`` (a built-in type, ``S<int>``)
* ``template parameter 'T' expects a type, but the argument supplied is a value`` (``S<4>`` for ``S<type T>``)

A name that is not declared at all is PSS002 (``unknown identifier``).

PSS100
------

**Severity:** error

Annotation is not attached to a model element

An annotation was written at the end of a scope with no following declaration to attach it to.  PSS 3.1 §7.13: *it is an error if no subsequent element is present in the scope*.

Message: ``annotation is not attached to a model element``

Either follow the annotation with the element it describes, or make it a standalone annotation by terminating it with ``;``, which attaches it to the enclosing scope.

PSS101
------

**Severity:** warning

Unknown annotation type (annotation disregarded)

An annotation names a type that is not declared.  This is a warning rather than an error: PSS 3.1 §7.13 requires that *PSS processing tools shall disregard unrecognized annotations*, so the surrounding source still compiles.

Message: ``unknown annotation type '<T>'; annotation disregarded``

If the annotation was meant to be recognized, check that its ``annotation`` declaration is visible -- annotation types must be declared at package scope.

PSS102
------

**Severity:** error

Annotation initializer is not a constant expression

An annotation parameter was given a value that cannot be evaluated at elaboration time.  PSS 3.1 §7.13 requires annotation attribute initializers to be constant expressions.

Message: ``annotation initializer for '<field>' is not a constant expression``

This check applies only to recognized annotation types; the contents of an unknown annotation are disregarded (PSS101).

PSS104
------

**Severity:** warning

Deprecated brace-less 'compile if' branch

A ``compile if`` branch consists of a single item that is not surrounded by braces.  This form remains supported, but is deprecated: prefer the braced form, which is unambiguous when the branch later grows to more than one item.

Message: ``'compile if' branch without enclosing braces is deprecated``

Before::

    compile if (X) component C { }

After::

    compile if (X) { component C { } }

The diagnostic underlines the whole unbraced branch and carries a related location pointing at the ``compile if`` keyword that owns it, which disambiguates the two warnings raised for an ``if``/``else`` pair.  Both branches are reported regardless of which one the condition selects: the spelling is deprecated either way, and warning only on the taken branch would make the diagnostic appear and disappear as unrelated configuration changed.

PSS105
------

**Severity:** error

Illegal 'mutable' qualifier

The ``mutable`` qualifier (PSS 3.1 §9.1.6) was applied where it is not permitted.  ``mutable`` may qualify component data declarations only, and is incompatible with the qualifiers listed in §9.1.6 a-c.

Message: ``illegal 'mutable' qualifier: <reason>``

PSS106
------

**Severity:** error

Exec block tag not permitted on this exec kind

An exec block tag (PSS 3.1 §5.1) was written on an exec kind that does not accept one.  Tags are permitted only on ``header``, ``declaration``, ``run_start``, ``run_end``, and ``exec file`` blocks -- not on native exec blocks, not on ``body``, and not on the solve execs (``init_down``, ``init_up``, ``pre_solve``, ``post_solve``, ``pre_body``).

Message: ``exec block tag is not permitted on '<kind>' exec blocks``

PSS107
------

**Severity:** error

Member selection on a slice

A member was selected from a slice of a collection.  A slice (``[a..b]``, ``[a..]``, ``[..b]``) denotes a sub-collection, not a single element, so it has no members of its own -- ``arr[1].f`` names a field of one element, while ``arr[1..3].f`` names a field of a list.

Message: ``member selection is not permitted on a slice of '<name>'``

Slices and plain indexes reach the resolver through the same subscript list, so before PSS 3.1 support a slice was silently resolved as though it were an index.

PSS108
------

**Severity:** error

Unterminated mustache expression

A ``{{`` inside a triple-quoted string was never closed by a matching ``}}`` (PSS 3.1 §4.7.1.1).

Message: ``unterminated mustache expression; if '{{' was intended as literal text, separate the braces ('{ {') -- triple-quoted strings have no escape mechanism``

The hint is not decoration.  PSS 3.1 makes ``{{`` open a mustache inside ``"""..."""`` and provides **no** escape mechanism, so target code that legitimately contains two adjacent open braces -- ``int m[2][2] = {{1,2},{3,4}};`` -- now fails here.  The conformant spelling is ``{ {``: a lone ``{`` is ordinary text, so separating the braces needs no escape and is read identically by every other PSS tool.

Note only the *opening* delimiter is special.  A stray ``}}`` in text is literal and is never reported, which is why C and C++ closing braces are unaffected.

PSS109
------

**Severity:** error

Malformed mustache expression

The content of a ``{{ ... }}`` did not parse as a PSS expression (PSS 3.1 §4.7.1.1).

Message: ``malformed mustache expression: <detail>; if '{{' was intended as literal text, separate the braces ('{ {')``

Syntax errors from the sub-parse are wrapped in this diagnostic rather than forwarded verbatim: a raw ``mismatched input '}' expecting ...`` rebased out of a fragment tells the user nothing about the real cause, which is most often the ``{{`` collision described under PSS108.

An unparseable mustache is deliberately an **error** and never silently-literal text.  Treating it as text would let a genuinely malformed ``{{ x + }}`` through unnoticed.

PSS110
------

**Severity:** error

Malformed or unterminated template directive or comment

A ``{% ... %}`` directive or ``{# ... #}`` comment inside a triple-quoted string is unterminated, does not parse, or opened a block that was never closed (PSS 3.1 §4.7.1.2, §4.7.1.3).

Messages:

* ``unterminated template directive``
* ``unterminated template comment``
* ``unclosed template block at end of string``
* ``malformed template directive: <detail>``

These carry no ``{ {`` hint, unlike PSS108/PSS109.  A malformed ``{%`` or ``{#`` cannot be produced by ordinary target code the way ``{{`` can, so the hint would be noise.

PSS111
------

**Severity:** error

Template block directive out of place

A block-closing or ``else`` directive appeared where no block was open (PSS 3.1 §4.7.1.2, Table 5).

Messages:

* ``template block close with no open block`` -- a ``{%%}`` too many
* ``'else' with no preceding 'if'``

Note a *duplicate* template-local declaration is reported as ``PSS003`` rather than here: it is the same defect as any other duplicate declaration and shares that message shape.

PSS112
------

**Severity:** error

Template assignment target is not a template local

A ``{% x = expr; %}`` directive assigned to something other than a variable declared earlier in the *same* triple-quoted string (PSS 3.1 §4.7.1.2).  Assigning to an action attribute is illegal.

Message: ``template assignment target '<name>' is not declared within this template string``

Nothing about the syntax distinguishes a legal template-local assignment from an illegal attribute assignment -- the only way to tell them apart is which symbol table the name resolved through.  Declare the variable with ``{% int x; %}`` inside the template, or drop the assignment.

PSS113
------

**Severity:** error

Template expression is not of scalar type

A ``{{ ... }}`` mustache expression is of aggregate type.  PSS 3.1 §4.7.1.1 requires the substituted expression to be of scalar type -- there is no defined text for a struct, a list or a map.

Message: ``template expression is not of scalar type``

Classification is the same coarse categoriser the argument checks use (PSS007), and it inherits that pass's known gaps (see ``known-issues.md`` P3-X6c): member paths, subscripts, nested calls and user-defined types are classified as *unknown*, and nothing is reported for an unknown category.  So this fires on a literal aggregate and on a field whose declared type is plainly aggregate, and stays silent elsewhere rather than guessing.

PSS114
------

**Severity:** error

Non-pure function called from a template string

A mustache expression or control-flow directive called a function that is not declared ``pure``.  PSS 3.1 §4.7.1.1: any function called from a template shall be pure, since expansion happens during elaboration and must not have side effects.

Message: ``call to non-pure function '<name>' in a template string``

Declare the function ``pure function ...`` if it is free of side effects, or compute the value outside the template and reference the result.

A function declared in a ``pure component`` is pure without carrying the qualifier itself, and is not reported.  Purity follows the type a function is *declared* in, so deriving from a pure component does not make the derived component's own functions pure.

PSS115
------

**Severity:** error

Non-constant template string where a constant is required

A triple-quoted string whose special elements reference something other than constants was used where a constant expression is required -- a ``const`` field initializer, or an annotation initializer (§4.7, §7.13a).

Message: ``template string with non-constant elements is not a constant expression``

Reported at the point of *use*, not at the template: the same template text is perfectly legal in an exec body.  A template is constant when every expression under every special element references only constants -- ``const`` fields, enum items, type template value parameters, and template locals derived from those.  A call is never constant, even to a ``pure`` function: this front end does not evaluate function bodies.

PSS116
------

**Severity:** warning

Construct is accepted but not represented in the AST

The grammar accepts this construct and the parse is sound, but the AST builder does not build a node for it -- or builds one that omits part of what was written.  A consumer walking the AST will not see the construct at all, or will see it without the detail named in the message.

Messages take one of two forms, where *construct* is the construct name in backticks:

* *construct* ``is accepted but not represented in the AST`` -- nothing is built for the construct.
* *construct* ``is accepted but not represented in the AST:`` *detail* -- a node is built, and *detail* names the part that is dropped.

This is a gap in the front end, not a problem with the source: the code is legal PSS.  There is nothing to fix in the input.  Suppress the marker if the construct is not material to how the AST is consumed; otherwise treat any analysis that depends on the named construct as unreliable.

The catalogue of affected constructs, and the plan for closing them, are in ``docs/ast-coverage-gaps.md`` and ``docs/ast-coverage-plan.md``.  As each construct is implemented its PSS116 disappears.

PSS117
------

**Severity:** warning

Traversal of a deprecated dynamic constraint

An activity traverses a ``dynamic`` constraint.  This still works, but LRM 13.1.1 deprecates dynamic constraints: "their functionality is replaced by a generic constraint with no parameters".

Message: ``traversal of dynamic constraint 'dc' is deprecated (13.1.1); declare it as a generic constraint, 'constraint dc() { ... }'``

Before::

    dynamic constraint dc { x > 0; }

After::

    constraint dc() { x > 0; }

Reported where the constraint is traversed.  Traversing a *fixed* named constraint is an error (PSS018).

PSS118
------

**Severity:** error

Constant initializer references a later or type-level constant

LRM 18.2c: a constant or enum item may be referenced in the initializer of another constant only after its declaration. LRM 18.2d: a package-level constant may reference only other package-level constants.  Messages:

* ``constant 'C' is used in the initializer of 'A' before its declaration on line 4; declare it first (18.2)`` (or ``enum item 'E_X' ...``, or ``... in a file given later``)
* ``constant 'A' is used in the initializer of 'A', which is itself (18.2)``
* ``package-level constant 'A' may reference only package-level constants; 'K' is declared in type 'C' (18.2)``

Before::

    package my {
      const int A = C;
      const int C = 3;
    }

After::

    package my {
      const int C = 3;
      const int A = C;
    }

Across files, the order the files are given in applies, as it does for ``compile if``.  Elsewhere in a type or package, declaration order does not matter (Example 262).  A name used before its declaration in an exec or activity block is PSS002; in a type width, PSS119.

PSS119
------

**Severity:** warning

Type width references a constant declared later

The prose under LRM Example 264 extends 18.2c to type-width expressions: a constant used in ``bit[W]`` must be declared before it.  Message: ``constant 'W' is used in a type width before its declaration on line 5; declare it first (18.2)``.

A warning rather than an error, because the rule is stated only in prose and existing models write it.  Move the constant's declaration above its first use.

