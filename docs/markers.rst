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
* ``'pkg' has no member named 'thing'``
* ``Failed to find elem 'thing'``

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

An ``extend`` declaration targets a type or enum that does not exist.  Messages include patterns such as:

* ``cannot extend unknown type 'Foo'``
* ``cannot extend unknown enum 'MyEnum'``

Ensure the base type is declared before or alongside the extend block.

PSS006
------

**Severity:** error

Call does not match the callee's parameters

A function call supplies more or fewer arguments than the callee declares, names something that is not a function, or the callee's parameter list is itself malformed.  Messages include patterns such as:

* ``too few arguments to 'f': expected 2, got 1``
* ``too many arguments to 'f': expected 1, got 2``
* ``'x' is not a function``
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
* ``parameter 1 ('a') of 'f' is given a default value by more than one declaration``

Reported once per function, against the declaration the rest of the tool treats as authoritative: a definition's prototype where there is one, otherwise the first.

The last of these is LRM 20.2.4 c, which forbids respecifying a default "even if the value is the same" -- so the values are never compared.  A default given by only one declaration is in effect for all of them.

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

Message: ``expected identifier before '<token>'``

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

