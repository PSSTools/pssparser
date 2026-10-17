Marker Reference
================

Every diagnostic the built-in core can emit, generated from
``CoreChecker.marker_defs`` by ``scripts/gen_marker_docs.py`` -- do not edit
this file by hand, it will be overwritten.  Query the same information from
the command line with ``--list-markers`` and ``--describe <ID>``.

Namespaces
----------

``PSS``
   Normative PSS: the model violates the language reference manual.
   ``PSS001``-``PSS099`` is the general band, ``PSS020``-``PSS028`` its
   syntax sub-band, and ``PSS100``-``PSS199`` the PSS 3.1 language-rule band.
``LINT``
   Lint: legal PSS that is probably not what the author meant.  The rules
   listed here are raised by the core linker; the full rule reference,
   grouped by family, is :doc:`lint-rules`.
``PSSP``
   pssparser itself: an extension failed to load, a construct is accepted
   but not represented in the AST, an old ID was used in a configuration.

Several warnings that used to carry ``PSS`` IDs moved to ``LINT`` or
``PSSP``.  Their old IDs are listed under *Retired and reserved codes*; they
are still accepted wherever an ID is typed (configuration, ``-W``,
``--describe``) and are never reused.

Severities
----------

``error``
   The model is invalid, or a finding was promoted with ``-Werror``.  Sets
   exit status 1.
``warning``
   Probably wrong; fix or waive it.  Exit status 0 unless ``-Werror``.
``info``
   Worth knowing, no action required.  Counted as a *note*; not promoted by
   a bare ``-Werror`` (use ``-Werror=info`` or ``-Werror=ID``).
``hint``
   An editor nudge.  Hidden at the command line unless ``--show-hints``;
   always present in machine-readable output.

PSS: LRM violations
-------------------

PSS001
~~~~~~

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
~~~~~~

**Severity:** error

Unknown symbol reference

The linker could not resolve a named type, identifier, or method.  Messages include patterns such as:

* ``unknown type 'Foo'``
* ``unknown type 'Foo' in 'pkg'`` (the name is not in the qualifying package or scope)
* ``unknown identifier 'bar'``
* ``unknown method 'baz' on built-in type``
* ``unknown function 'f': an import of this form needs a separate declaration of the function (20.4.1)``
* ``'pkg' has no member named 'thing'``, or ``'f()' has no member named 'thing'`` for a member of a call's result; with ``; did you mean 'thang'?`` when a member is spelled close to it
* ``'this' is only valid inside a type: ...`` (``this`` in a package-level function)
* ``'super' is only valid inside a type that has a base type, and 'S' has none`` (also ``'super;'``)
* ``'comp' is only valid in an action declared in a component, and 'AB' is declared outside one``
* ``'prev' is only valid in a state type or its extension, and cannot be reached as a member of 'i'``
* ``base type 'B' has no member named 'x'`` (``super.x``)
* ``cannot resolve 'y': the enclosing scope is unknown`` (``x[0].y`` where x's element type did not resolve)
* ``'tx' is a component instance, not a type or package; did you mean 'tx_c'?`` -- 18.3: only a package or a type qualifies a name, so an instance, field, variable, function or symbol cannot, even where its type declares the name (9.1.3, Example 47).  The suggestion is the qualifier's declared type, offered only when it declares the name

Ensure the symbol is declared in one of the source files passed to pssparser, or that the correct package is imported.  When a close match exists, a ``did you mean '...'?`` suggestion is appended.

PSS003
~~~~~~

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
~~~~~~

**Severity:** error

Symbol or ref-path resolution failure

A symbol or reference path could not be resolved during linking.  Messages include patterns such as:

* ``failed to resolve ref-path <path>``
* ``failed to resolve symbol <name>``
* ``root ref-path element <x> is not a composite scope``

Check that all referenced symbols are declared and that composite-type fields are used correctly.

PSS005
~~~~~~

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
~~~~~~

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
* ``argument 1 of 'g' is an aggregate literal, so parameter 's' must be declared const (LRM 20.2.3)``, and ``argument 2 of 'g' is constant 'C', so parameter 'd' must be declared const (LRM 20.2.3)`` -- a constant of aggregate type passes only to a const parameter of a PSS function (Example 291)
* ``argument 1 of 'sum' is an array of 3 elements, but parameter 'v' is an array of 2 (LRM 8.3)``
* ``argument 1 of 's' is a value, but parameter 'h' is a handle of action 'A'`` -- a symbol's action-handle parameter takes a handle of that action type or a subtype, or an element of an array of them (11.7)

Argument types are compared only by broad category -- numeric, string, composite.  Widths, signedness and struct subtyping are deliberately not judged, except that a symbol's handle argument must be of the parameter's action type or a subtype.

Parameters with a default may be omitted, which is why the bound is reported as ``at least``/``at most`` when the two differ.  A ``type... args`` parameter removes the upper bound entirely.

PSS007
~~~~~~

**Severity:** error

Return type used inconsistently

A ``return`` supplies a value from a ``void`` function, omits one where a return type is declared, or the result of a ``void`` call is used as a value.  Messages include patterns such as:

* ``'f' returns void, so 'return' cannot take a value``
* ``'f' has a return type, so 'return' must supply a value``
* ``'f' returns void, so its result cannot be used as a value``
* ``an exec block returns void, so 'return' cannot take a value (LRM 20.7.5, ruling R21)`` -- 20.7.5 permits only the bare ``return;`` in an exec

The last of these is LRM 20.5: a void function "may only be called as a standalone procedural statement".  The converse -- calling a non-void function as a statement and discarding the result -- is explicitly legal and is not reported.

Taking a member of a call result counts as using it, so ``f().x`` on a void ``f`` is reported here rather than as a resolution failure.  A *scalar* return is not: ``f().x`` on an int-returning ``f`` gets the same PSS004 message a scalar variable would.

Whether a non-void function returns on *every* path is not checked.

PSS008
~~~~~~

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
~~~~~~

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
~~~~~~

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
~~~~~~

**Severity:** error

Digit out of range for a based literal's radix

A based literal (LRM B.19, e.g. ``'hFF``, ``8'b1010``) contains a digit that is not valid for its radix -- for example a hex literal spelled with a letter past ``f``/``F``. The lexer accepts any alphanumeric run after the radix character so a typo still lexes as one literal token (rather than a lexical error splitting the trailing characters into an unrelated token); this check then validates the digits against the radix. Only the first invalid digit is reported. Message: ``invalid digit '<c>' in based literal``.

PSS012
~~~~~~

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
~~~~~~

**Severity:** error

Type extension adds a field to a packed struct

LRM 21.13.1: "Type extensions of packed structs shall not add new fields." A packed struct's layout is fixed by its declaration; an ``extend`` elsewhere must not change it. Constraints, exec blocks and ``static const`` members may still be added. Message: ``type extension of packed struct '<s>' adds field '<f>'; an extension of a packed struct may not add fields``.

PSS014
~~~~~~

**Severity:** error

Register value type has no size, or is wider than the register

``reg_c<R, ACC, SZ>`` (LRM 21.14.1) lays a value of type ``R`` over a register ``SZ`` bits wide. ``R`` must have a known packed size -- a packed struct, or another packable type such as ``bit[N]``, ``int[32]`` or an enum with a base type -- and ``SZ``, when given, must be at least ``sizeof_s<R>::nbits``. (Omitting ``SZ`` gives ``8*sizeof_s<R>::nbytes``, which always fits.) Messages include:

* ``reg_c value type is struct 'cfg_s', which is not packed; derive it from packed_s<>``
* ``reg_c value type is enum 'mode_e', which has no base type; ...``
* ``reg_c width SZ = 32 is smaller than its value type 'desc_s' (40 bits)``

Reported where the register type is used (``reg_c<...>`` as a field type or a base type), not in the core library.

PSS015
~~~~~~

**Severity:** error

sizeof_s of a type that has no packed size

LRM 21.13.2.1: ``sizeof_s<>`` "shall not be parameterized with types other than numeric types, Booleans, enumerated types that have a base type, packed structs, and arrays thereof." Such a specialization has no ``nbits`` or ``nbytes`` value. Message: ``sizeof_s argument is <what>, which has no packed size``, or ``sizeof_s argument is <what>; <how to fix it>``. A packed struct with a bad member is reported at the member (PSS012), not here.

PSS017
~~~~~~

**Severity:** error

Ambiguous name: more than one import provides it

LRM 18.1.3: when two imports of the same kind make the same name visible, and they name different declarations, the name is not imported at all. An explicit import (``import p::s;``) takes precedence over a wildcard import (``import p::*;``), so only imports of the same kind can conflict. Two imports that reach the same declaration do not conflict.  Message: ``ambiguous reference to 's': more than one wildcard import provides it, so none does (18.1.3); qualify the name``. Qualify the name (``lib1::s``) or import it explicitly.  The same holds for a field or type that extensions in two packages add to one type, where both packages are wildcard-imported (17.2.3): ``ambiguous reference to 'b': extensions of 'S' in package 'p' and package 'q' each declare it, and each package is imported here (17.2.3); import only one``.

PSS018
~~~~~~

**Severity:** error

Traversal of something that is not an action

An action traversal statement names something that cannot be traversed.  LRM 11.3.1: the identifier "names a unique action handle or variable in the context of the containing action type or activity scope"; a variable may be a data field declared with the ``action`` modifier, which is randomized with no execution (Example 173).  A generic constraint (13.4.11), a deprecated ``dynamic`` constraint (see LINT602) and a symbol may also be traversed.  Messages include:

* ``'x' is not an action handle, and cannot be traversed; only a handle, or a data field declared with the 'action' modifier, can be``
* ``'A' is a type, not an action handle; traverse it by type with 'do A'``
* ``'L1' is an activity label, not an action handle, and cannot be traversed``
* ``'c' is a fixed constraint, which always holds and cannot be traversed; ...`` -- write it as a generic constraint, ``constraint c() { ... }``
* ``'S' is not an action type, and cannot be traversed`` (``do S`` on a struct or component)
* ``'s' is a symbol, not an action handle; a symbol takes no 'with' constraints (11.7)`` (also ``no initializer list``): ``s;`` activates a symbol, but it has no fields to constrain or set

A name that is not declared at all is PSS002.

PSS019
~~~~~~

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
~~~~~~

**Severity:** error

Expected specific punctuation before this token

The parser reached a point where only one or two specific punctuation tokens could legally continue the construct, and the next token was not one of them. Messages include patterns such as:

* ``expected ';' before '<token>'``
* ``expected '{' or ':' before '<token>'``
* ``expected '{' or ':' before 'extends'; use ':' for inheritance, not 'extends'``

Insert the missing punctuation, or (for the last case) replace ``extends`` with ``:``.

``expected ';' before '<token>'`` is also reported when a statement that could have ended with ``;`` is followed, on the next line, by a token that starts another statement: ``int a = 1, b = 2`` or ``f(1)`` with no ``;`` before the next line.  The marker is on the next line's first token, since that is where the parser noticed.  When the line ends in a name, the marker moves to the end of that line instead (``expected ';' after '<name>'``).

PSS021
~~~~~~

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
~~~~~~

**Severity:** error

Expected an identifier before this token

The grammar requires an identifier at this position and the next token is not one. Reached via either of ANTLR's two recovery strategies for the same situation: single-token-insertion (offending token already in the follow set, e.g. ``;``, ``{``, ``=``) or a full mismatched-input exception whose expecting-set is exactly identifier-shaped (``{ID, ESCAPED_ID}``, optionally with a leading ``'::'``) -- which is how a real PSS keyword used where an identifier belongs (``struct``, ``return``, ...) lands here too. There is no reachable keyword sub-case distinct from this one -- **PSS023 is reserved, not assigned**.

Messages:

* ``expected identifier before '<token>'``
* ``'this' is a keyword and cannot be used as a declared name`` -- the one keyword the lexer returns as an identifier, so the grammar accepts it and the declaration is rejected afterwards

PSS024
~~~~~~

**Severity:** error

Unexpected token in this context

A general ``mismatched input`` case that PSS020, PSS021, and PSS022 do not cover more specifically: the token is not one of the (possibly several) tokens that could legally appear here. Messages include patterns such as:

* ``unexpected '<token>' in this context`` (the expecting set was too large to usefully quote)
* ``unexpected '<token>' expecting {<alternatives>}`` (the expecting set was small enough to show)

PSS025
~~~~~~

**Severity:** error

Unexpected punctuation in this context

A single punctuation token appears where nothing could legally follow.

Message: ``unexpected '<token>' in this context``

The same wording as PSS024's first pattern; the two differ only in which ANTLR exception produced them (``extraneous input`` here, ``mismatched input`` there).

PSS026
~~~~~~

**Severity:** error

Unexpected token in this context (non-punctuation)

As PSS025, but the extraneous token is not a single punctuation character -- a keyword, a multi-character operator, or a literal. Only called a "keyword" in the message when it actually looks like one (starts with a letter or ``_``); anything else, such as a numeric literal, gets the plain PSS025-style wording while keeping this ID. Messages include patterns such as:

* ``unexpected keyword '<token>' in this context``
* ``unexpected '<token>' in this context`` (non-keyword-looking offender, e.g. ``123``)

PSS027
~~~~~~

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
~~~~~~

**Severity:** error

Syntax error (unclassified alternative)

ANTLR could not decide among the grammar's alternatives at this point (a ``no viable alternative`` exception) and no more specific rewrite applies.

Message: ``syntax error at '<token>'``

The message does not say what was expected; work outward from the enclosing construct to find the mistake.

PSS040
~~~~~~

**Severity:** error

Instance member used without an instance

A reference reaches a field or function that belongs to an instance of a type from a place that has no instance to take it from.  Messages include patterns such as:

* ``'fld' is an instance member of 'sub_c' and cannot be referenced through the type; only types, static constants, static functions and enum items can (18.3)``
* ``cannot reference instance member 'fld' from static function 'st_f': a static function has no component instance (20.2)``

LRM 18.3: a type's namespace holds types, static constants, static functions and enum items, so ``T::m`` cannot name an ordinary field or an instance function; reach it through an instance with ``.`` instead.  A reference written inside ``T``, a subtype of ``T`` or an extension of either is not reported, since a base-qualified call there has an instance to use.  A ``const`` field is treated as a constant.

LRM 20.2: a static component function is not associated with an instance, so its body cannot read the component's non-static fields or call its instance functions.  Make the member static, pass the value in as a parameter, or drop ``static`` from the function.

PSS041
~~~~~~

**Severity:** error

Static member used through 'comp'

An action reaches a static function or static constant of a component through its ``comp`` handle.  Messages include patterns such as:

* ``cannot reach static member 'f' of 'my_c' through 'comp'; name it without 'comp.', as 'f' (9.1.4.1 f)``
* ``cannot reach static member 'K' of 'sub_c' through 'comp'; name it through the type instead, as 'sub_c::K' (9.1.4.1 f)``

LRM 9.1.4.1 f: "It shall be illegal to access static component members using the comp handle."  ``comp`` is an instance; a static member belongs to the component type (20.2.1.1 c).  A member of the action's own component is found by its plain name, since the action is declared inside that component or an extension of it; a member of a sub-component is named through its type, ``sub_c::f``.  Reported for every path that starts at ``comp``, including ``comp.sub.f()``.

PSS042
~~~~~~

**Severity:** error

Reference left unbound (pssparser defect)

The linker finished without binding a name, although the model declares something of that name, and without saying why.  This is a defect in pssparser, not necessarily in the model: please report it together with the input.  Message:

* ``'x' was left unbound by pssparser, although the model declares it: a pssparser defect, please report it``

Reported by the completeness check that runs after linking (symbol-resolution plan 3.5), so that a consumer is never handed a reference with no target in silence.  It is reported only on a model with no other error; with one, an unbound name is far more likely a consequence of that error.  A name that nothing in the model declares is PSS002 instead.  Some constructs are not checked yet: covergroup bodies and port maps, instance overrides, the member names of a struct literal whose type is not known from where it is written, and a bind target past a component whose type is unknown or generic.

PSS043
~~~~~~

**Severity:** error

Illegal package alias declaration

LRM 18.1.4 restricts the name of a package alias (``import pkg1::a::b as p1;``).  Messages:

* ``package alias 'X' is already declared in this scope; two aliases in one scope shall not share a name (18.1.4)``
* ``package alias 'foo' has the same name as a package declared in package 'P'; rename the alias (18.1.4)``

Two aliases in one lexical scope -- one ``package`` statement, component declaration or extension, or one file's global scope -- shall not have the same name; the same name in two statements of one package is legal.  An alias shall not take the name of a package declared in the same namespace in this source unit or an earlier one (Example 260).  A package of that name added in a later source unit is legal, and from then on a reference finds the package rather than the alias (18.3 c.1 before c.2.i).

PSS047
~~~~~~

**Severity:** error

Template argument of the wrong kind

A template parameter is either a value parameter or a type parameter (10.3), and its argument has to be of the same kind.  A name spells a type and a constant alike, so ``S<X>`` is decided by what ``X`` names: for a value parameter, ``X`` is looked up as a value -- an enum item of the parameter's enumeration type first (18.3 a), then the usual scopes -- and a type found there is reported.  Messages:

* ``template parameter 'N' expects a value, but 'my_s' is a type``
* ``template parameter 'N' expects a value, but the argument supplied is a type`` (a built-in type, ``S<int>``)
* ``template parameter 'T' expects a type, but the argument supplied is a value`` (``S<4>`` for ``S<type T>``)

A name that is not declared at all is PSS002 (``unknown identifier``).

PSS048
~~~~~~

**Severity:** error

Invalid struct literal member

A struct literal names the data attributes of its context type (4.8.4): the type of the field or variable it initializes, the left-hand side of the assignment, the parameter it is passed for, the function's return type, an exec block's tag type, or the enclosing literal's member (4.8.5).  Each attribute may be named once.  Messages:

* ``struct literal names 'a' more than once (4.8.4)``
* ``struct literal names 'c1', which is not a data attribute of 'S1' (4.8.4)`` (a constraint, say)

A name the context type does not declare at all is PSS002 (``'S1' has no member named 'x'``).

PSS049
~~~~~~

**Severity:** error

Invalid bind operand

A pool bind (12.3) names a pool, then for each target a path of component instances from the binding component, an action type of the last component reached, and an input, output or resource-claim field of that action type.  Messages:

* ``bind names 'x', which is not a pool (12.3)``
* ``bind names 'x', which is not a component instance of 'C' (12.3)``
* ``bind names 'x', which is not an action type of 'C' (12.3)``
* ``bind names 'x', which is not an input, output or resource-claim field of 'A' (12.3)``

A name that is not declared where it is looked up is PSS002 (``'C' has no member named 'x'``).

PSS050
~~~~~~

**Severity:** error

Invalid coverage reference

A cross crosses coverpoints of its covergroup, or variables, each of which is an implicit coverpoint (15.1 d, 15.4).  A bin written ``bins b = cp with (...)`` names its own coverpoint (15.3.3.3), and a cross bin its own cross (15.4.3).  Messages:

* ``cross 'X' names 'f', which is not a coverpoint or a data field (15.4)``
* ``bins 'b' names 'a', which is not its own coverpoint 'c' (15.3.3.3)``
* ``bins 'b' names 'Y', which is not its own cross 'X' (15.4.3)``

A name that is not declared at all is PSS002.

PSS051
~~~~~~

**Severity:** error

Extension member not visible here

A member an extension adds to a type is accessible in the package the extension is written in, and elsewhere only where that package is wildcard-imported (17.2.3, 18.1.3).  An extension in the global scope, or in the package that declares the type, is visible wherever the type is.  Messages:

* ``'b' is declared by an extension of 'S' in package 'p', which is not visible here (17.2.3); add 'import p::*;'``
* ``'B' is an item an extension of 'E' in package 'p' adds, which is not visible here (17.2.3); add 'import p::*;'``

The use still binds to the member, so later diagnostics are measured against it.  A warning in pssparser 3.1.7; an error since (symbol-resolution plan §8).  Where two imported packages each add the name, the use is ambiguous: PSS017.

PSS052
~~~~~~

**Severity:** error

Explicit import conflicts with a declaration or import

18.1.3: it shall be illegal to explicitly import an identifier the importing namespace already declares, or to explicitly import the same identifier from two different packages.  Messages:

* ``'import lib::s;' names 's', which package 'p' already declares; an explicit import shall not name a declaration of the importing namespace (18.1.3)``
* ``'s' is already imported explicitly in this scope, by 'import lib1::s;'; the same name shall not be imported explicitly from two packages (18.1.3)``

The namespace is every statement of a package, or a component and its extensions; two imports conflict only within one statement.  A warning in pssparser 3.1.7; an error since (plan §8).  A use of a name two explicit imports provide is PSS017.

PSS054
~~~~~~

**Severity:** error

compile assert failed

19.4: a ``compile assert`` whose condition is false.  Messages:

* ``compile assert failed: too wide`` -- the condition folded when the file was read; the string is the assertion's own message, when it has one
* ``compile assert failed for 'S<64>': too wide`` -- an assertion in a generic type's body that names a template parameter (Ex. 71-73).  It has a value only in a specialization, so each specialization is checked once linked, and reported at the first use that creates it, with a related location at the assertion.  The generic itself is never checked.

PSS055
~~~~~~

**Severity:** error

Compile-time condition cannot be evaluated

19.1.3, 19.4: the condition of a ``compile if`` or ``compile assert`` must be determinable at compile time.  Messages:

* ``compile if condition cannot be evaluated at compile time: 'X > 1'. ...`` -- it names something that is not a constant, or one declared in a later file (19.1.2)
* ``compile assert condition cannot be evaluated for 'S<4>': ...`` -- an assertion on a template parameter that does not fold in that specialization

PSS056
~~~~~~

**Severity:** error

Template arguments given to a type that is not generic

A type that declares no template parameters was written with an argument list, in a use (``t<1> f;``) or in an instance extension (``extend struct t<1>``, 17.2.6b).  Message: ``'t' is not a generic type, so it takes no template arguments``.  Remove the argument list.

PSS057
~~~~~~

**Severity:** error

Extension of a type inside a template instance

``extend struct C<2>::s``, or an ``extend struct s`` written inside ``extend component C<2>``, extends a type declared in one instance of a generic component.  pssparser does not support this.  An extension of the instance's own members (``extend component C<2> { int x; }``) is supported (17.2.6b).

PSS058
~~~~~~

**Severity:** error

Extension kind does not match the type

An ``extend`` statement names the kind of type it extends, and LRM 17.2 requires it to agree with the type: ``extend action M`` where ``M`` is a monitor, or ``extend struct b`` where ``b`` is a buffer, or ``extend struct e`` where ``e`` is an enum.  The message gives the kind to write.  ``extend enum s`` where ``s`` is not an enum is PSS005.  The extension's members are not added to the type.

PSS059
~~~~~~

**Severity:** error

Cyclic inheritance

A type inherits, directly or through its base types, from itself: ``struct S : S``, or ``A : B`` and ``B : A``.  Message: ``cyclic inheritance: 'A' -> 'B' -> 'A'``, which names every type on the ring, in inheritance order.  It is reported once per ring.  Names looked up through the inheritance chain of a type on the ring are not searched past it.

PSS060
~~~~~~

**Severity:** error

Template argument list does not match the parameters

A use of a generic type supplies the wrong number of template arguments (LRM 10).  Messages:

* ``'array' takes 2 template arguments, but 3 are given`` -- too many
* ``no value supplied for template parameter 'N', and it has no default`` -- too few, for a value parameter
* ``no type supplied for template parameter 'T', and it has no default`` -- too few, for a type parameter (``list<> x;``)
* ``template type 'P' requires a template argument list`` -- a generic named with no list at all, as the qualifier of ``P::nbytes``

Supply an argument for each parameter that has no default.

PSS061
~~~~~~

**Severity:** error

Template argument does not satisfy its parameter

A type argument is of the wrong kind for its parameter (LRM 10.3.2).  Messages:

* ``template parameter 'T' requires an argument of type category 'struct', but the argument 'c' is of category 'component'`` -- the parameter was declared ``struct T``
* ``template parameter 'T' is restricted to 'base_s' and its subtypes, but the argument 'x_s' does not derive from 'base_s'`` -- the parameter was declared ``struct T : base_s``

PSS062
~~~~~~

**Severity:** error

Recursive template specialization does not terminate

Specializing a generic type specializes it again with a strictly larger argument, so the chain never reaches a specialization that already exists: ``struct S<type T> { S<S<T>> next; }``.  pssparser stops at a fixed depth and reports it at the generic's declaration.  Message: ``recursive specialization of 'S' exceeded the maximum depth of N: ...``

PSS063
~~~~~~

**Severity:** error

Invalid override action

An action declared ``override`` in a component replaces the action of that name in a base component (LRM 9.2.2).  Messages:

* ``cannot override action 'A': no action of that name is declared in a base component of 'C'``
* ``cannot override template action 'A'`` -- a generic action cannot be overridden
* ``action 'A' must be declared 'override': 'C' declares it as an override action`` -- an action that redeclares an override action's name needs the keyword too

PSS064
~~~~~~

**Severity:** error

A symbol activates itself

LRM 11.7: "A symbol may activate another symbol, but symbols are not recursive and may not activate themselves."  The activations are the calls ``s(...)`` and the ``s;`` form of Example 120 in a symbol's body.  A cycle is reported once, at the activation that closes it, naming the chain:

* ``symbol 's1' activates itself: s1 -> s2 -> s1 (11.7)``
* ``symbol 's' activates itself: s -> s (11.7)``

PSS100
~~~~~~

**Severity:** error

Annotation is not attached to a model element

An annotation was written at the end of a scope with no following declaration to attach it to.  PSS 3.1 §7.13: *it is an error if no subsequent element is present in the scope*.

Message: ``annotation is not attached to a model element``

Either follow the annotation with the element it describes, or make it a standalone annotation by terminating it with ``;``, which attaches it to the enclosing scope.

PSS102
~~~~~~

**Severity:** error

Annotation initializer is not a constant expression

An annotation parameter was given a value that cannot be evaluated at elaboration time.  PSS 3.1 §7.13 requires annotation attribute initializers to be constant expressions.

Message: ``annotation initializer for '<field>' is not a constant expression``

This check applies only to recognized annotation types; the contents of an unknown annotation are disregarded (LINT403).

PSS105
~~~~~~

**Severity:** error

Illegal 'mutable' qualifier

The ``mutable`` qualifier (PSS 3.1 §9.1.6) was applied where it is not permitted.  ``mutable`` may qualify component data declarations only, and is incompatible with the qualifiers listed in §9.1.6 a-c.

Message: ``illegal 'mutable' qualifier: <reason>``

PSS106
~~~~~~

**Severity:** error

Exec block tag not permitted on this exec kind

An exec block tag (PSS 3.1 §5.1) was written on an exec kind that does not accept one.  Tags are permitted only on ``header``, ``declaration``, ``run_start``, ``run_end``, and ``exec file`` blocks -- not on native exec blocks, not on ``body``, and not on the solve execs (``init_down``, ``init_up``, ``pre_solve``, ``post_solve``, ``pre_body``).

Message: ``exec block tag is not permitted on '<kind>' exec blocks``

PSS107
~~~~~~

**Severity:** error

Member selection on a slice

A member was selected from a slice of a collection.  A slice (``[a..b]``, ``[a..]``, ``[..b]``) denotes a sub-collection, not a single element, so it has no members of its own -- ``arr[1].f`` names a field of one element, while ``arr[1..3].f`` names a field of a list.

Message: ``member selection is not permitted on a slice of '<name>'``

Slices and plain indexes reach the resolver through the same subscript list, so before PSS 3.1 support a slice was silently resolved as though it were an index.

PSS108
~~~~~~

**Severity:** error

Unterminated mustache expression

A ``{{`` inside a triple-quoted string was never closed by a matching ``}}`` (PSS 3.1 §4.7.1.1).

Message: ``unterminated mustache expression; if '{{' was intended as literal text, separate the braces ('{ {') -- triple-quoted strings have no escape mechanism``

The hint is not decoration.  PSS 3.1 makes ``{{`` open a mustache inside ``"""..."""`` and provides **no** escape mechanism, so target code that legitimately contains two adjacent open braces -- ``int m[2][2] = {{1,2},{3,4}};`` -- now fails here.  The conformant spelling is ``{ {``: a lone ``{`` is ordinary text, so separating the braces needs no escape and is read identically by every other PSS tool.

Note only the *opening* delimiter is special.  A stray ``}}`` in text is literal and is never reported, which is why C and C++ closing braces are unaffected.

PSS109
~~~~~~

**Severity:** error

Malformed mustache expression

The content of a ``{{ ... }}`` did not parse as a PSS expression (PSS 3.1 §4.7.1.1).

Message: ``malformed mustache expression: <detail>; if '{{' was intended as literal text, separate the braces ('{ {')``

Syntax errors from the sub-parse are wrapped in this diagnostic rather than forwarded verbatim: a raw ``mismatched input '}' expecting ...`` rebased out of a fragment tells the user nothing about the real cause, which is most often the ``{{`` collision described under PSS108.

An unparseable mustache is deliberately an **error** and never silently-literal text.  Treating it as text would let a genuinely malformed ``{{ x + }}`` through unnoticed.

PSS110
~~~~~~

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
~~~~~~

**Severity:** error

Template block directive out of place

A block-closing or ``else`` directive appeared where no block was open (PSS 3.1 §4.7.1.2, Table 5).

Messages:

* ``template block close with no open block`` -- a ``{%%}`` too many
* ``'else' with no preceding 'if'``

Note a *duplicate* template-local declaration is reported as ``PSS003`` rather than here: it is the same defect as any other duplicate declaration and shares that message shape.

PSS112
~~~~~~

**Severity:** error

Template assignment target is not a template local

A ``{% x = expr; %}`` directive assigned to something other than a variable declared earlier in the *same* triple-quoted string (PSS 3.1 §4.7.1.2).  Assigning to an action attribute is illegal.

Message: ``template assignment target '<name>' is not declared within this template string``

Nothing about the syntax distinguishes a legal template-local assignment from an illegal attribute assignment -- the only way to tell them apart is which symbol table the name resolved through.  Declare the variable with ``{% int x; %}`` inside the template, or drop the assignment.

PSS113
~~~~~~

**Severity:** error

Template expression is not of scalar type

A ``{{ ... }}`` mustache expression is of aggregate type.  PSS 3.1 §4.7.1.1 requires the substituted expression to be of scalar type -- there is no defined text for a struct, a list or a map.

Message: ``template expression is not of scalar type``

Classification is the same coarse categoriser the argument checks use (PSS007), and it inherits that pass's known gaps (see ``known-issues.md`` P3-X6c): member paths, subscripts, nested calls and user-defined types are classified as *unknown*, and nothing is reported for an unknown category.  So this fires on a literal aggregate and on a field whose declared type is plainly aggregate, and stays silent elsewhere rather than guessing.

PSS114
~~~~~~

**Severity:** error

Non-pure function called from a template string

A mustache expression or control-flow directive called a function that is not declared ``pure``.  PSS 3.1 §4.7.1.1: any function called from a template shall be pure, since expansion happens during elaboration and must not have side effects.

Message: ``call to non-pure function '<name>' in a template string``

Declare the function ``pure function ...`` if it is free of side effects, or compute the value outside the template and reference the result.

A function declared in a ``pure component`` is pure without carrying the qualifier itself, and is not reported.  Purity follows the type a function is *declared* in, so deriving from a pure component does not make the derived component's own functions pure.

PSS115
~~~~~~

**Severity:** error

Non-constant template string where a constant is required

A triple-quoted string whose special elements reference something other than constants was used where a constant expression is required -- a ``const`` field initializer, or an annotation initializer (§4.7, §7.13a).

Message: ``template string with non-constant elements is not a constant expression``

Reported at the point of *use*, not at the template: the same template text is perfectly legal in an exec body.  A template is constant when every expression under every special element references only constants -- ``const`` fields, enum items, type template value parameters, and template locals derived from those.  A call is never constant, even to a ``pure`` function: this front end does not evaluate function bodies.

PSS118
~~~~~~

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

Across files, the order the files are given in applies, as it does for ``compile if``.  Elsewhere in a type or package, declaration order does not matter (Example 262).  A name used before its declaration in an exec or activity block is PSS002; in a type width, LINT404.

PSS121
~~~~~~

**Severity:** error

A constant or a const parameter is assigned

LRM 7.1: "The value of constant fields can be read but not modified. A constant cannot appear on the left-hand side of the assignment operator", and "If the constant is of aggregate type, its elements are constants too."  LRM 20.2.3: a const parameter "cannot be changed in the function body".  Messages:

* ``constant 'C' cannot be assigned: a constant cannot appear on the left of an assignment (LRM 7.1)``
* ``an element or member of constant 'TBL' cannot be assigned: a constant's elements are constants too (LRM 7.1)``
* ``parameter 'x' is const, so its value cannot be changed in the function body (LRM 20.2.3)``
* ``an element or member of const parameter 's' cannot be changed in the function body (LRM 20.2.3)``

A compound assignment (``C += 1``) is an assignment.  Passing a constant of aggregate type to a non-const parameter is PSS006.

PSS122
~~~~~~

**Severity:** error

Sub-string on the left of an assignment

LRM 7.6.2: "The sub-string operator shall not be used on the left-hand side of an assignment operator."  An index or a slice of a string is a sub-string (8.6.3), so ``s[0] = "x"`` is an error; assign the whole string instead.  An element of an array of strings is not a sub-string: ``ss[1] = "x"`` is legal.

PSS123
~~~~~~

**Severity:** error

A foreach changes its index, iterator or collection

LRM 20.7.8 g: "The index and iterator variables are read-only. Their values shall not be changed within the foreach body. It shall be an error to change the contents of the iterated collection variable with[in] the foreach body."  An assignment to the collection or to what holds it, and a call of a method that changes it (``push_back``, ``insert``, ``delete``, ``clear``, ...), are reported.  An assignment to an element is not: the LRM's own Example 291 assigns ``dst[i]`` in ``foreach (dst[i])``; nor is a member of the iterator, which aliases the element (20.7.8 c), only the iterator written whole.  Messages:

* ``foreach index variable 'i' is read-only and cannot be changed in the foreach body (LRM 20.7.8 g)``
* ``foreach iterator variable 'e' is read-only ...``
* ``'w' is the collection this foreach iterates, so it cannot be changed in the foreach body (LRM 20.7.8 g)``

PSS124
~~~~~~

**Severity:** error

break or continue outside a loop

LRM 20.7.11 b: "break and continue may only appear within loop statements (repeat-count, repeat-while or foreach). Within a loop, break and continue may be nested in conditional branch or match statements."

PSS125
~~~~~~

**Severity:** error

A match statement has more than one default branch

LRM 20.7.10 f (procedural) and 11.4.6 f (activity): "The default branch is optional. There may be at most one default branch in the match statement."  The second and any later ``default`` is reported.

PSS126
~~~~~~

**Severity:** error

A cast from or to a type that cannot be cast

LRM 7.12: "Expressions of types int, bit, bool, enum, or floating-point type can be changed to another type in this list by using a cast operator. In addition, an expression of a reference type can be changed to a compatible reference type."  7.12.1: "A type_identifier specified as a casting_type shall refer to a numeric, Boolean, enumeration, or reference type", and a) "A numeric, Boolean, or enumeration value can only be cast to another numeric, Boolean or enumeration type."  Messages:

* ``a cast to struct p_s: a casting type shall be a numeric, Boolean, enumeration or reference type (LRM 7.12.1)``
* ``a cast from chandle: only a numeric, Boolean or enumeration value, or a reference, can be cast (LRM 7.12)``

A cast from a chandle, a string, a struct or a collection is illegal only because 7.12 does not list it.

PSS127
~~~~~~

**Severity:** error

'in' with a range list and a non-scalar left side

LRM 8.5.9.1: "The left-hand side shall not be an unqualified enum_item (see 7.5) or an aggregate literal", and "If the expression on the left-hand side is of a scalar type, the right-hand side may be an open_range_list or a collection_expression. Otherwise, the right-hand side shall be a collection_expression."  ``p in [1]`` with ``p`` a struct is an error; ``p in list_of_p`` is legal.

PSS128
~~~~~~

**Severity:** error

An operator applied to an array of components or actions

LRM 7.9.2: arrays of modeling elements may be indexed with ``[]``, "However, other operators and methods do not apply to these arrays, unless otherwise specified" -- ``size()``, ``foreach`` and ``in`` are.  ``s == t`` and ``s = t`` on arrays of components are reported.

PSS129
~~~~~~

**Severity:** error

A function signature uses a component, action or object type without ref

LRM 20.2.2: "Functions shall not return action types, component types, or flow/resource object types without the ref modifier", and "Functions shall not have parameters of action types, component types, or flow/resource object types without the ref modifier."  Messages:

* ``function 'g' returns component type 'sub_c' without 'ref': a function shall not (LRM 20.2.2)``
* ``parameter 'b' of 'f' has flow object type 'b_s' without 'ref': a function shall not (LRM 20.2.2)``

PSS130
~~~~~~

**Severity:** error

Unqualified enum item where its enumeration type is not expected

An enum item belongs to its enumeration type's scope, not to the scope that declares the enum (7.5.1 g).  Unqualified, it is found only where the expression's expected type is that enumeration type (7.5.1 i, 8.4.3, 18.3 a): an assignment or initializer, a call argument, a ``return``, the RIGHT side of ``==``/``!=``, the values of ``in``, a cast to the enum, and the arms of ``?:``.  The left side of ``==`` has no expected type, and 8.5.9.1: "The left-hand side [of in] shall not be an unqualified enum_item".  pssparser finds an item of an enclosing scope's enum anyway, when the name means nothing else, and reports it: an error by ruling R22 (it was the warning LINT101).  Messages:

* ``enum item 'ORANGE' is used where no enumeration type is expected (7.5.1 i, 8.4.3; ruling R22); qualify it as 'color_e::ORANGE'``
* ``enum item 'RED' is used where 'mode_e' is expected, but it is an item of 'color_e' (7.5.1 i, 8.4.3; ruling R22); qualify it as 'color_e::RED'``

Qualify the item.  LRM Example 37: ``print_num((int)ORANGE)`` is an error, because the cast's type is ``int``.

PSS131
~~~~~~

**Severity:** error

An operand of a type its operator does not take

LRM 8.4 Table 10 says which operand types each operator takes (Table 9 for the compound assignments): ``-``, ``+``, ``*``, ``/``, ``**`` and the relational operators take numeric operands (8.5.1, 8.5.2: "may be applied only to numeric operands"); ``%``, ``~``, the bitwise, reduction and shift operators, ``&=``, ``|=``, ``<<=`` and ``>>=`` take integer ones; ``!``, ``&&`` and ``||`` Boolean ones.  So a relational operator on bool or string, the chained ``a < b < c``, a bitwise operator on bool, ``%`` on a float and ``+`` on strings are errors.  7.7: a chandle is compared only with a chandle, and "the only literal value with which it may be compared is 0".  An enum operand is not judged here (7.5.1 permits it in assignment and equality).  Messages:

* ``operator '<' takes numeric operands, not bool (LRM 8.4 Table 10, 8.5.2)``
* ``a chandle can be compared only with a chandle or the literal 0, not int (LRM 7.7)``

PSS132
~~~~~~

**Severity:** error

A condition that is not Boolean

The condition of ``if`` (20.7.9), ``while`` and ``repeat ... while`` (20.7.7 a: "expression shall be of type bool") and of ``?:`` (8.5.8: "cond_predicate shall be of Boolean type") is a Boolean.  ``if (x)`` with an integer ``x`` is an error; write ``if (x != 0)``.

PSS133
~~~~~~

**Severity:** error

null assigned to what is not a reference

LRM 8.3: the right side of an assignment shall be assignment-compatible with the left; ``null`` is the value of a reference (7.10).  ``int y = null;`` is an error.  A chandle is not judged.

PSS134
~~~~~~

**Severity:** error

Enum item values: a duplicate, or outside the base type

LRM 7.5.1 e: "Each enum_item shall have a distinct integer value" -- across the declaration and its extensions.  7.5.1 c: with a base type, "It shall be an error to explicitly assign a value which does not belong to the base type" (a negative value with an unsigned base, say), and to give an item no value when the previous one has the base type's greatest value.  7.5.1: the base type "shall not have a value domain".  An item whose value does not fold here (one defined by another item) ends the check for its enum.  Messages:

* ``enum item 'B' has the value 1, as 'A' does: each enum item shall have a distinct value (LRM 7.5.1 e)``
* ``enum item 'A' has the value -1, which is not a value of the base type bit[4] (LRM 7.5.1 c)``
* ``enum item 'B' has no value of its own, and the item before it has the greatest value of the base type bit[2] (LRM 7.5.1 c)``
* ``the base type of enum 'h_e' shall not have a value domain (LRM 7.5.1)``

PSS135
~~~~~~

**Severity:** error

A variable of an enum with no items

LRM 7.5.1 j: an enum may be declared with no items and given them in extensions, but "It shall be illegal to declare an enumeration variable whose type contains no enum_items across its initial definition and extensions."

LINT: core-emitted lint
-----------------------

LINT301
~~~~~~~

**Severity:** warning

**Name:** ``exported-instance-function``; **Tier:** suspicious; **Family:** exec; **Formerly:** ``PSS120``

Exported function is a component instance function

20.4.2 allows ``export target function f;`` to name only a static function: a package function or a component's ``static`` one.  Naming a component's INSTANCE function is an extension, meaning the function is run on the instance the environment calls it through.  pssc's operation models take their API from it.  Message: ``exported function 'f' is not static; exporting a component's instance function is an extension to 20.4.2``.

A warning, not an error: the export is bound all the same, so a tool that implements the extension can use it.  A strictly conforming model declares the function ``static``.

LINT401
~~~~~~~

**Severity:** warning

**Name:** ``enum-item-hides-declaration``; **Tier:** suspicious; **Family:** decl; **Formerly:** ``PSS044``

Enum item hides a declaration of the same name

Where an expression's expected type is an enumeration type (8.4.3), an unqualified name is looked up among that enum's items before any scope (18.3 a).  A field, variable or parameter of the same name is then hidden, which is legal but rarely intended.  Message:

* ``'A' is read as the enum item mode_e::A, which hides the field 'A' (18.3 a); qualify one of them``

Write ``mode_e::A`` for the item, or rename the field.

LINT402
~~~~~~~

**Severity:** warning

**Name:** ``import-after-declaration``; **Tier:** style; **Family:** import; **Formerly:** ``PSS053``

Import after a declaration

18.1.3: import specifications shall appear first in their lexical scope -- a file's global scope, a ``package`` statement, or a component declaration or extension.  Only another import or a ``compile if`` may precede one.  Message:

* ``'import lib::*;' follows a declaration; imports shall come first in a package, a component, an extension or a file (18.1.3)``

Not checked in a scope that holds a ``compile if``.

Severity: ``warning``, although the ``style`` tier defaults to ``hint``.  This was a core warning before lint existed, and the ``minimal`` profile keeps the output it always had.

LINT403
~~~~~~~

**Severity:** warning

**Name:** ``unknown-annotation``; **Tier:** portability; **Family:** decl; **Formerly:** ``PSS101``

Unknown annotation type (annotation disregarded)

An annotation names a type that is not declared.  This is a warning rather than an error: PSS 3.1 §7.13 requires that *PSS processing tools shall disregard unrecognized annotations*, so the surrounding source still compiles.

Message: ``unknown annotation type '<T>'; annotation disregarded``

If the annotation was meant to be recognized, check that its ``annotation`` declaration is visible -- annotation types must be declared at package scope.

LINT404
~~~~~~~

**Severity:** warning

**Name:** ``width-references-later-constant``; **Tier:** portability; **Family:** decl; **Formerly:** ``PSS119``

Type width references a constant declared later

The prose under LRM Example 264 extends 18.2c to type-width expressions: a constant used in ``bit[W]`` must be declared before it.  Message: ``constant 'W' is used in a type width before its declaration on line 5; declare it first (18.2)``.

A warning rather than an error, because the rule is stated only in prose and existing models write it.  Move the constant's declaration above its first use.

LINT501
~~~~~~~

**Severity:** warning

**Name:** ``reg-width-no-access-function``; **Tier:** suspicious; **Family:** register; **Formerly:** ``PSS016``

Register width has no primitive access function

LRM 21.14.5a translates register reads and writes into the primitive ``read8/16/32/64`` and ``write8/16/32/64`` functions (21.13.9), chosen by the register's size. A register ``SZ`` bits wide, where ``SZ`` is not 8, 16, 32 or 64, has no such function, so its access cannot be translated as the spec describes. Not a "shall" in the spec, so a warning. A packed struct of any size is legal on its own -- a 96-bit DMA descriptor, say; this is only about using one as a register value type. Message: ``reg_c width SZ = 96 has no primitive access function; use 8, 16, 32 or 64 bits``. For a register whose value type is narrower than a primitive, give ``SZ`` explicitly (``reg_c<my12_s, READWRITE, 16>``).

LINT601
~~~~~~~

**Severity:** warning

**Name:** ``deprecated-braceless-compile-if``; **Tier:** portability; **Family:** evolution; **Formerly:** ``PSS104``

Deprecated brace-less 'compile if' branch

A ``compile if`` branch consists of a single item that is not surrounded by braces.  This form remains supported, but is deprecated: prefer the braced form, which is unambiguous when the branch later grows to more than one item.

Message: ``'compile if' branch without enclosing braces is deprecated``

Before::

    compile if (X) component C { }

After::

    compile if (X) { component C { } }

The diagnostic underlines the whole unbraced branch and carries a related location pointing at the ``compile if`` keyword that owns it, which disambiguates the two warnings raised for an ``if``/``else`` pair.  Both branches are reported regardless of which one the condition selects: the spelling is deprecated either way, and warning only on the taken branch would make the diagnostic appear and disappear as unrelated configuration changed.

LINT602
~~~~~~~

**Severity:** warning

**Name:** ``deprecated-dynamic-constraint-traversal``; **Tier:** portability; **Family:** evolution; **Formerly:** ``PSS117``

Traversal of a deprecated dynamic constraint

An activity traverses a ``dynamic`` constraint.  This still works, but LRM 13.1.1 deprecates dynamic constraints: "their functionality is replaced by a generic constraint with no parameters".

Message: ``traversal of dynamic constraint 'dc' is deprecated (13.1.1); declare it as a generic constraint, 'constraint dc() { ... }'``

Before::

    dynamic constraint dc { x > 0; }

After::

    constraint dc() { x > 0; }

Reported where the constraint is traversed.  Traversing a *fixed* named constraint is an error (PSS018).

PSSP: the tool's own diagnostics
--------------------------------

PSSP000
~~~~~~~

**Severity:** error

**Name:** ``internal-error``; **Tier:** tool; **Formerly:** ``PSS000``

Internal error

pssparser reached a state it believed could not happen.  This is a defect in pssparser, not necessarily in the model, and it should be reported together with the input that triggers it.  The message names the phase or link pass that failed:

* ``internal error in resolving references: ...``
* ``internal error while building the AST: ...``

Results for the rest of the model are incomplete: the pass that failed stopped, and the passes after it did not run.  The command-line tool exits with status 3 when an internal error is reported.

PSSP001
~~~~~~~

**Severity:** warning

**Name:** ``extension-load-failed``; **Tier:** tool; **Formerly:** ``PSS030``

A checker extension could not be loaded

An entry point in the ``pssparser.extensions`` (or legacy ``pssparser.checkers``) group failed to load. The usual causes are an import error inside the extension, an exception raised from its ``register()`` function, or a module that exposes neither ``register()`` nor the ``CHECKERS`` shorthand.

The run continues: a third-party extension is code you did not write, and one broken package must not stop the rest of the registry from loading. The consequence is that the rules that extension contributes did **not** run, so a clean result is not evidence of clean source.

Use ``--list-extensions`` to see what did load, and ``--no-extensions`` (or ``PSSPARSER_NO_EXTENSIONS=1``) to confirm the behaviour is the extension's and not pssparser's. In CI, ``-Werror=PSSP001`` makes a failed extension fatal, which is usually what you want.

PSSP002
~~~~~~~

**Severity:** warning

**Name:** ``entry-point-name-mismatch``; **Tier:** tool; **Formerly:** ``PSS031``

Entry-point key disagrees with the checker's declared name

A legacy ``pssparser.checkers`` entry point is keyed under one name while the class it names declares another in its ``name`` attribute.

The class is authoritative -- it is the name the checker reports itself under and the name ``--checker`` and ``--no-checker`` select -- so the checker is registered under the declared name and the entry-point key is ignored. Rename the key to match; while they disagree, a command line written against the key silently selects nothing.

PSSP003
~~~~~~~

**Severity:** warning

**Name:** ``extension-api-too-new``; **Tier:** tool; **Formerly:** ``PSS032``

Extension requires a newer checker API than this build provides

The extension declared ``requires_api = N`` (as a module level ``REQUIRES_API`` or on the registry inside ``register()``) and ``N`` is greater than this build's ``pssparser.checkers.API_VERSION``.

The extension is not loaded, deliberately: refusing here produces one clear message, where loading it anyway produces an ``AttributeError`` from inside a checker halfway through a run. Upgrade pssparser, or install a build of the extension made for this API version.

PSSP004
~~~~~~~

**Severity:** info

**Name:** ``deprecated-alias``; **Tier:** tool

An old marker ID was used where an ID is accepted

A configuration key, ``-W`` flag or other ID-accepting input named a code that has moved -- for example ``PSS104``, which is now ``LINT601``.  The old code still works: it is rewritten to the new one, and this note says so once per spelling, naming where it was written.  Update the input to the new ID to silence the note.

Codes move when their meaning is reclassified: a warning about legal code is lint (``LINT``), and a diagnostic about pssparser itself is ``PSSP``; ``PSS`` is kept for LRM violations.

PSSP005
~~~~~~~

**Severity:** error

**Name:** ``reserved-namespace``; **Tier:** tool

A checker declares a marker ID in a reserved namespace

The ``PSS``, ``LINT``, ``PSSP`` and ``PSSX`` namespaces belong to pssparser, with or without a team qualifier (``PSS-ACME001`` is refused too).  A checker from an installed extension that declares an ID in one of them is not registered; the rest of its extension still loads.  Choose a namespace of your own -- two to five capital letters, then three digits (``PRC001``).

PSSP006
~~~~~~~

**Severity:** warning

**Name:** ``malformed-marker-id``; **Tier:** tool

A checker declares a marker ID that does not fit the ID grammar

Marker IDs are a namespace of two to five capital letters, optionally followed by ``-`` and a team of two to five more, then three digits (``PRC001``, ``ACME-NET001``).  An ID that does not fit still loads, for now, but cannot be selected by namespace or band and will be refused in a later release.  Rename it.

PSSP007
~~~~~~~

**Severity:** error

**Name:** ``too-many-errors``; **Tier:** tool; **Formerly:** ``PSS029``

Too many errors; stopped reporting further errors

``--max-errors`` (default 20; ``0`` disables the cap) was reached for this file. Only error-severity markers count against it -- warnings and hints never trigger it, and a clean file never sees it. Emitted once, at the location of the error that pushed the count over the limit; every further error in that file is dropped, not merely hidden, so re-running with a higher (or ``0``) ``--max-errors`` is the only way to see what comes after it.

Message: ``too many errors (<N>); stopped reporting further errors for this file``

PSSP008
~~~~~~~

**Severity:** error

**Name:** ``duplicate-marker-id``; **Tier:** tool; **Formerly:** ``PSS033``

Two checkers declare the same marker ID

Marker IDs are globally unique across the core and every installed extension. Two rules wearing one ID make ``--describe``, ``-Werror=ID`` and every per-ID severity override ambiguous, so the collision is an error rather than a warning.

The checker that lost the collision is not registered; everything else, including the rest of its extension, still loads. The message names both contributors. The fix belongs in the extension: pick an unused namespace -- two to five capital letters, then three digits (``PRC001``).  The ``PSS``, ``LINT``, ``PSSP`` and ``PSSX`` namespaces belong to pssparser (``PSSP005``).

PSSP101
~~~~~~~

**Severity:** warning

**Name:** ``construct-not-represented``; **Tier:** tool; **Formerly:** ``PSS116``

Construct is accepted but not represented in the AST

The grammar accepts this construct and the parse is sound, but the AST builder does not build a node for it -- or builds one that omits part of what was written.  A consumer walking the AST will not see the construct at all, or will see it without the detail named in the message.

Messages take one of two forms, where *construct* is the construct name in backticks:

* *construct* ``is accepted but not represented in the AST`` -- nothing is built for the construct.
* *construct* ``is accepted but not represented in the AST:`` *detail* -- a node is built, and *detail* names the part that is dropped.

This is a gap in the front end, not a problem with the source: the code is legal PSS.  There is nothing to fix in the input.  Suppress the marker if the construct is not material to how the AST is consumed; otherwise treat any analysis that depends on the named construct as unreliable.

The catalogue of affected constructs, and the plan for closing them, are in ``docs/ast-coverage-gaps.md`` and ``docs/ast-coverage-plan.md``.  As each construct is implemented its PSSP101 disappears.

PSSP201
~~~~~~~

**Severity:** warning

**Name:** ``bad-rule-metadata``; **Tier:** tool

A lint rule's metadata is invalid

A ``MarkerDef`` with lint metadata breaks one of the rules in the plug-in guide's *Rule metadata* section: a name that is not unique or not kebab-case, a tier, family or level outside its closed set, a ``LINT`` ID with no tier, a ``nursery`` rule with no ``since``, a fix with no example showing it, or a severity that differs from the tier's default without a ``Severity:`` paragraph in ``detail``.  The message names the field.  The checker is not registered.

PSSP202
~~~~~~~

**Severity:** warning

**Name:** ``unused-waiver``; **Tier:** tool

A waiver matched no diagnostic

A ``@lint_pkg::waive`` annotation or ``// pssparser waive`` comment covered no diagnostic, although a rule it names ran on this run.  Usually the code it excused has been fixed: delete the waiver.  A waiver for a rule that did not run -- turned off, outside the lint profile, or from a checker that was not loaded -- is not reported, so a waiver does not flap with the configuration.

PSSP203
~~~~~~~

**Severity:** warning

**Name:** ``unknown-waiver-rule``; **Tier:** tool

A waiver names no known rule

The ``id`` of a ``@lint_pkg::waive`` annotation, or an ID in a ``// pssparser waive`` comment, is not a marker ID, rule name or selector that any loaded checker declares.  Usually a typo; the message suggests the nearest match.  A rule from an extension that is not installed looks the same.

PSSP204
~~~~~~~

**Severity:** warning

**Name:** ``waiver-on-error``; **Tier:** tool

A waiver names an error that cannot be waived

An LRM error means the model was not built, so waiving it would report success for a run that compiled nothing.  The waiver has no effect.  Fix the error, and delete the waiver.

PSSP205
~~~~~~~

**Severity:** warning

**Name:** ``waiver-without-reason``; **Tier:** tool

A waiver gives no reason

Every waiver says why: ``.reason`` in the annotation, or the text after ``:`` in the comment.  The waiver still applies; this asks for the reason.

PSSP206
~~~~~~~

**Severity:** info

**Name:** ``stale-baseline-entry``; **Tier:** tool

A baseline entry matched fewer findings than it recorded

The baseline records a finding that this run no longer reports: it was fixed, or the code changed enough to be a different finding.  The diagnostic points at the entry in the baseline file.  Rewrite the baseline with ``--write-baseline`` so that the finding cannot come back unnoticed.  It is reported only for an entry whose file was checked and whose rule ran, so checking a subset of the files, or turning a rule off, does not make entries stale.

PSSP210
~~~~~~~

**Severity:** error

**Name:** ``rule-file-structure``; **Tier:** tool

A rule file is not a pss-rules file

The file is refused as a whole: it is empty, its top level is not a mapping with the single key ``pss-rules``, ``pss-rules`` is not a mapping or has no ``rules`` list, or it declares a ``version`` this pssparser does not read.  A file of a later version is never partly loaded; the message names both versions.

PSSP211
~~~~~~~

**Severity:** error

**Name:** ``rule-unknown-key``; **Tier:** tool

A rule file has a key the format does not define

Rule files are strict: an unknown key is an error, never ignored, so a misspelt ``wher:`` cannot leave a rule firing on every node.  The message suggests the nearest key.  A key in a rule disables that rule.  Keys starting with ``x-`` are the author's own and are ignored.  Settings beside ``pss-rules`` at the top level belong under it.

PSSP212
~~~~~~~

**Severity:** error

**Name:** ``rule-field-invalid``; **Tier:** tool

A rule field is missing or has a wrong value

A required field is missing (``id``, ``name``, ``tier``, ``summary``, ``message``, ``match``; ``since`` in the nursery tier; ``family``, ``doc`` and examples that fire and do not fire in a built-in rule), or a field has the wrong type or a value outside its set.  This includes ``options`` specs, ``let`` names, example expectations, a field under ``defaults`` that cannot be defaulted, and ``fix``, which is reserved.  The rule is not loaded.

PSSP213
~~~~~~~

**Severity:** error

**Name:** ``rule-unknown-kind``; **Tier:** tool

A rule's match names an unknown node kind

``match.kind``, ``inside`` and ``not_inside`` name AST classes from the schema (``ast/*.yaml``), as ``ExprBin`` or ``Action``.  The message suggests the nearest class.  The rule is not loaded.

PSSP214
~~~~~~~

**Severity:** error

**Name:** ``rule-expression-syntax``; **Tier:** tool

A rule expression is not valid CEL

A ``where``, ``report``, ``let``, ``define`` or message ``${...}`` expression does not parse, or uses a part of CEL that pss-rules leaves out (see ``docs/lint-functions.rst``).  The position is mapped back to the line and column in the rule file.  Write CEL in a block scalar (``>-``) or a quoted string, since ``:``, ``#`` and ``?`` would otherwise trip YAML.  In a message, ``$${`` is a literal ``${``.

PSSP215
~~~~~~~

**Severity:** error

**Name:** ``rule-expression-type``; **Tier:** tool

A rule expression does not type-check

Every expression has a static type, checked when the rule loads: an unknown name, field, function or option, a wrong argument type, ``where`` that is not a bool, ``report`` that is not a list of nodes, or a message interpolation that is not a string, number, bool or node.  The rule is not loaded.

PSSP216
~~~~~~~

**Severity:** error

**Name:** ``rule-expression-limit``; **Tier:** tool

A rule expression exceeds a limit

Comprehensions nest more than two deep in one expression or helper (move the inner part into a ``define:`` helper), ``define:`` helpers call each other in a cycle (the message gives the path), or a regular expression is outside the supported RE2 syntax.  These limits keep every rule's run time bounded.  The rule is not loaded.

PSSP217
~~~~~~~

**Severity:** error

**Name:** ``rule-id-conflict``; **Tier:** tool

A rule's ID or name is reserved or already taken

A site rule file may not use the ``PSS``, ``PSSP``, ``PSSX`` or ``LINT`` namespaces, with or without a team qualifier (``LINT-NET001`` is refused too); a built-in rule file uses ``LINT`` only.  Across every loaded rule file and extension, a rule's ID and aliases are unique among IDs and aliases, and its name among names; the message names the other rule's file and line.  Team namespaces are separate: ``ACME-NET001`` and ``ACME-DMA001`` do not clash.  The rule is not loaded.

PSSP218
~~~~~~~

**Severity:** error

**Name:** ``rule-file-yaml``; **Tier:** tool

A rule file is not valid YAML for pss-rules

A YAML syntax error, a duplicate key, a tag (``!!str``), or more than one document in the file.  The file is refused as a whole.  Rule files use YAML 1.2 core-schema scalars: ``yes``, ``no``, ``on`` and ``off`` are strings.

PSSP219
~~~~~~~

**Severity:** info

**Name:** ``rule-helper-shadowed``; **Tier:** tool

A rule's helper shadows the file's helper of the same name

A ``define:`` helper of a rule has the name of a file-level helper, so within that rule it replaces the file's.  That may be intended; rename one of them if it is not.

PSSP220
~~~~~~~

**Severity:** warning

**Name:** ``rule-evaluation-error``; **Tier:** tool

A lint rule failed while evaluating

A rule's ``where``, ``report`` or message expression evaluated to an error on a node: most often a field read through an unset one (``node.super_t.elems`` on a type with no base), which a rule guards with ``has()`` or ``.?``.  The message names the rule, the expression and the node.  The rule is skipped for the rest of that file, once; the other rules still run.  A finding whose message failed is kept, with ``?`` in place of the failed part.  The model is not at fault: fix the rule, or turn it off.

PSSP221
~~~~~~~

**Severity:** warning

**Name:** ``rule-budget-exceeded``; **Tier:** tool

A lint rule used up its evaluation budget for a file

Each rule may spend a fixed number of evaluation steps on each file, counted across every node it matches, so a costly rule cannot stall the editor.  A rule that runs out is skipped for the rest of that file; the findings it already made stand, and the other rules still run.  The message names the rule and the node it was evaluating.  Make the rule cheaper: a narrower ``match``, or a ``where`` that rejects early.

PSSP222
~~~~~~~

**Severity:** error

**Name:** ``rule-example-failed``; **Tier:** tool

A lint rule's example does not give the findings it expects

``pssparser --check-rules`` runs each rule's ``examples:``: every example is parsed and linked on its own, and only its rule runs.  The rule must report exactly where the example's ``// expect:`` comments say, and nowhere else; an example with no ``expect`` must report nothing.  An example that does not parse or link, or on which the rule fails, fails too.  The marker is at the example in the rule file, and its message gives the position in the example's text.  Fix the rule or the example: an example is the rule's documentation, so the two must agree.

PSSP223
~~~~~~~

**Severity:** info

**Name:** ``rule-unknown-type``; **Tier:** tool

A lint rule names a type the model does not have

A rule's ``type_named`` or ``derives_from`` names a PSS type (``acme::claim_s``) that is not in the model being checked: a typo, or a package that was not compiled in.  The rule still runs, with ``type_named`` giving ``optional.none()`` and ``derives_from`` false for that name, so it may report nothing.  The note is given once per rule and name, at the node the rule was evaluating when it first asked.  Fix the name, or add the package's files to the run.

PSSP230
~~~~~~~

**Severity:** info

**Name:** ``lint-skipped``; **Tier:** tool

Lint did not run because the model has errors

Lint rules run only on a model that parsed, linked and passed the semantic checks without an error, since a rule on a broken model would report noise.  The message gives the number of errors.  Fix them, and lint runs.

Retired and reserved codes
--------------------------

PSS000
~~~~~~

**Retired: replaced by ``PSSP000``**

Internal error (moved to PSSP000)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP000`` (``internal-error``). ``PSS000`` is still accepted wherever an ID is typed, and is never reused.

PSS016
~~~~~~

**Retired: replaced by ``LINT501``**

Register width has no primitive access function (moved to LINT501)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT501`` (``reg-width-no-access-function``). ``PSS016`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS023
~~~~~~

**Reserved**

Reserved: keyword used where an identifier is expected

Allocated for a keyword-used-as-identifier sub-case of the syntax band, which turned out to be unreachable: the case is reported as PSS022.  Reserved, not assigned.

PSS029
~~~~~~

**Retired: replaced by ``PSSP007``**

Too many errors; stopped reporting further errors (moved to PSSP007)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP007`` (``too-many-errors``). ``PSS029`` is still accepted wherever an ID is typed, and is never reused.

PSS030
~~~~~~

**Retired: replaced by ``PSSP001``**

A checker extension could not be loaded (moved to PSSP001)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP001`` (``extension-load-failed``). ``PSS030`` is still accepted wherever an ID is typed, and is never reused.

PSS031
~~~~~~

**Retired: replaced by ``PSSP002``**

Entry-point key disagrees with the checker's declared name (moved to PSSP002)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP002`` (``entry-point-name-mismatch``). ``PSS031`` is still accepted wherever an ID is typed, and is never reused.

PSS032
~~~~~~

**Retired: replaced by ``PSSP003``**

Extension requires a newer checker API than this build provides (moved to PSSP003)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP003`` (``extension-api-too-new``). ``PSS032`` is still accepted wherever an ID is typed, and is never reused.

PSS033
~~~~~~

**Retired: replaced by ``PSSP008``**

Two checkers declare the same marker ID (moved to PSSP008)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP008`` (``duplicate-marker-id``). ``PSS033`` is still accepted wherever an ID is typed, and is never reused.

PSS044
~~~~~~

**Retired: replaced by ``LINT401``**

Enum item hides a declaration of the same name (moved to LINT401)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT401`` (``enum-item-hides-declaration``). ``PSS044`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS045
~~~~~~

**Retired**

Ambiguous enum item in a comparison (withdrawn; see PSS130)

Read ``a == b`` both ways, each side's type being the other side's expected type, and reported a comparison of two bare names either of which could be an item of the other's enum.  Ruling R22 gives the left side no expected type (8.4.3), so the ambiguity cannot arise: an unqualified item on the left is PSS130.  ``PSS045`` is never reused.

PSS046
~~~~~~

**Retired: replaced by ``LINT101``**

Enum item used where its enumeration type is not expected (moved to LINT101)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT101`` (``enum-item-type-mismatch``). ``PSS046`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS053
~~~~~~

**Retired: replaced by ``LINT402``**

Import after a declaration (moved to LINT402)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT402`` (``import-after-declaration``). ``PSS053`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS101
~~~~~~

**Retired: replaced by ``LINT403``**

Unknown annotation type (annotation disregarded) (moved to LINT403)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT403`` (``unknown-annotation``). ``PSS101`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS103
~~~~~~

**Retired**

Retired: annotation type declared outside package scope

Allocated for an annotation type declared outside package scope (7.13b), but the grammar reaches ``annotation_declaration`` only from ``package_body_item``, so the construct is a syntax error before any linker check could run.  Never emitted, and never reused.

PSS104
~~~~~~

**Retired: replaced by ``LINT601``**

Deprecated brace-less 'compile if' branch (moved to LINT601)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT601`` (``deprecated-braceless-compile-if``). ``PSS104`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS116
~~~~~~

**Retired: replaced by ``PSSP101``**

Construct is accepted but not represented in the AST (moved to PSSP101)

A diagnostic about pssparser itself, not about the model, so it moved to the ``PSSP`` namespace as ``PSSP101`` (``construct-not-represented``). ``PSS116`` is still accepted wherever an ID is typed, and is never reused.

PSS117
~~~~~~

**Retired: replaced by ``LINT602``**

Traversal of a deprecated dynamic constraint (moved to LINT602)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT602`` (``deprecated-dynamic-constraint-traversal``). ``PSS117`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS119
~~~~~~

**Retired: replaced by ``LINT404``**

Type width references a constant declared later (moved to LINT404)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT404`` (``width-references-later-constant``). ``PSS119`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

PSS120
~~~~~~

**Retired: replaced by ``LINT301``**

Exported function is a component instance function (moved to LINT301)

A lint rule, not an LRM violation, so it moved to the ``LINT`` namespace as ``LINT301`` (``exported-instance-function``). ``PSS120`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

LINT101
~~~~~~~

**Retired**

Enum item used where its enumeration type is not expected (now PSS130)

Retired: ruling R22 made this warning an error, reported as ``PSS130`` (it had moved here from ``PSS046``).  ``LINT101`` is still accepted wherever an ID is typed -- configuration, ``-W``, ``--describe`` -- and is never reused.

