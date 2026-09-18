r"""Authored `cause:` / `not_cause:` / `names:` terms, per case.

Input to `tools/backfill_cause.py`. This file is the authoring work; the script
is only the mechanical insert-and-renumber.

**Written from the defect, never from a tool's output.** Design §5.6: a rubric
tuned to agree with the tool it grades finds nothing. Nothing here was written
with a run file open.

Three rules keep the terms fair:

* **`cause:` is the minimum an accurate message must contain** — the construct
  noun and, where there is one, the offending lexeme from the source. One or
  two terms. More terms is not stricter, it is just a lower score for a message
  that said the right thing in different words.
* **`not_cause:` is words only, never punctuation.** Punctuation matches as a
  substring (a `;` term hits any message containing a semicolon), and
  `not_cause` is the only input that can score a message 0. A false 0 there is
  the worst failure the rubric has.
* **`identifier` is the term for "this declaration has no name."** It is the
  LRM's word. A message saying "name" instead scores 2 rather than 3, which is
  a nudge toward the spec's vocabulary and not a claim that the message is
  wrong.

`\,` is a literal comma (see `case._split_list`): several cases here are
missing-separator defects whose accurate message says `','`.
"""

TERMS: dict[str, dict[str, str]] = {}


def add(case_id, cause=None, not_cause=None, names=None):
    entry = {}
    if cause:
        entry["cause"] = cause
    if not_cause:
        entry["not_cause"] = not_cause
    if names:
        entry["names"] = names
    TERMS[case_id] = entry


# -- syntax.braces --------------------------------------------------------
#
# For an unterminated construct the accurate message names *which construct*
# was left open (design §5.5's D1 lever 1: blame the construct, not the token
# the parser choked on). For the two extra-`}` cases the sharp misdiagnosis is
# the opposite claim -- calling a surplus brace an unterminated one sends the
# reader to the wrong end of the file -- so those carry a `not_cause`.

add("SYN-BRACES-EXTRA-CLOSE-BRACE-AFTER-STRUCT", "}", "unterminated, unclosed",
    names="S")
add("SYN-BRACES-EXTRA-CLOSE-BRACE-COMPONENT", "}", "unterminated, unclosed",
    names="C")
add("SYN-BRACES-TRUNCATED-MID-ACTION-BODY", "exec", names="A")
add("SYN-BRACES-UNCLOSED-ACTION-BODY", "action", names="A")
add("SYN-BRACES-UNCLOSED-COMPONENT", "component", names="C")
add("SYN-BRACES-UNCLOSED-COMPONENT-OPENER-POINTER", "component", names="C")
add("SYN-BRACES-UNCLOSED-CONSTRAINT-BLOCK", "constraint", names="S")
add("SYN-BRACES-UNCLOSED-ENUM", "enum", names="E")
add("SYN-BRACES-UNCLOSED-STRUCT", "struct", names="S")
add("SYN-BRACES-UNCLOSED-STRUCT-OPENER-POINTER", "struct", names="S")
add("SYN-BRACES-UNEXPECTED-EOF", "struct", names="S")


# -- syntax.names ---------------------------------------------------------
#
# Two families: a declaration with no name at all, and a declaration whose
# name is not a legal identifier. Both want the construct plus `identifier`;
# what separates them is D3, not D1.

add("SYN-NAMES-ACTION-NO-NAME", "action, identifier", names="C")
add("SYN-NAMES-ACTION-NUMERIC-NAME", "action, identifier", names="C")
add("SYN-NAMES-COMPONENT-DASHED-NAME", "component, identifier")
add("SYN-NAMES-COMPONENT-NO-NAME", "component, identifier")
add("SYN-NAMES-ENUM-NO-NAME", "enum, identifier")
add("SYN-NAMES-EXPECTED-IDENTIFIER", "identifier", names="S")
add("SYN-NAMES-FIELD-NO-NAME", "identifier", names="S")
add("SYN-NAMES-FUNCTION-NO-NAME", "function, identifier")
add("SYN-NAMES-PACKAGE-NO-NAME", "package, identifier")
add("SYN-NAMES-STRUCT-NO-NAME", "struct, identifier")
add("SYN-NAMES-STRUCT-NUMERIC-NAME", "struct, identifier")
# `x @ }` -- the stray token is the defect; naming it is the whole message.
add("SYN-NAMES-EXPECTED-IDENTIFIER-AFTER-GARBAGE-TOKEN", "@", names="x")
# `struct S { 123 x; }` -- an integer literal where a type name belongs.
add("SYN-NAMES-UNCLASSIFIED-SYNTAX-ERROR", "type", names="S")
# `struct S { int x, }` -- a separator where a terminator belongs.
add("SYN-NAMES-UNEXPECTED-TOKEN", r"\,", names="x")


# -- syntax.punct ---------------------------------------------------------
#
# `not_cause: unknown type` on the missing-semicolon-between-declarations
# cases is the classic: `int x` newline `int y` reparses as a declaration of
# type `x`, and blaming the type sends the reader to look for a typedef that
# was never the problem. Design §5.1's D1=1 example is exactly this shape.

add("SYN-PUNCT-CASCADE-GARBAGE-TOKENS", "@")
add("SYN-PUNCT-EXPECTED-PUNCTUATION", ";", "unknown type", names="x")
add("SYN-PUNCT-EXTRA-TRAILING-COMMA-CALL", r"\,", names="foo")
add("SYN-PUNCT-MISSING-CLOSE-PAREN-CALL", ")", names="foo")
add("SYN-PUNCT-MISSING-COMMA-CALL-ARGS", r"\,", names="foo")
add("SYN-PUNCT-MISSING-COMMA-FIELDS", r"\,", names="x")
add("SYN-PUNCT-MISSING-OPEN-BRACE-COMPONENT", "{", names="C")
add("SYN-PUNCT-MISSING-SEMICOLON", ";", "unknown type", names="x")
add("SYN-PUNCT-MISSING-SEMICOLON-AFTER-BITFIELD", ";", names="y")
add("SYN-PUNCT-MISSING-SEMICOLON-CONSTRAINT", ";")
add("SYN-PUNCT-MISSING-SEMICOLON-FIELD", ";", "unknown type", names="x")
add("SYN-PUNCT-MISSING-SEMICOLON-IMPORT", ";", names="std_pkg")
add("SYN-PUNCT-MISSING-SEMICOLON-RETURN", ";")
# `x == 5;` as a statement: a comparison written where an assignment belongs.
add("SYN-PUNCT-UNEXPECTED-DOUBLE-EQUAL-STMT", "==", names="x")
add("SYN-PUNCT-UNEXPECTED-PUNCTUATION", "*")


# -- syntax.expr ----------------------------------------------------------
#
# Operator-position defects: the accurate message quotes the operator or says
# an operand is missing. `expression` is the term where nothing was written at
# all and there is no lexeme to quote.

add("SYN-EXPR-DANGLING-DOT", ".", names="x")
add("SYN-EXPR-DANGLING-PLUS-SEMICOLON", "+", names="x")
add("SYN-EXPR-EMPTY-PARENS-EXPR-POSITION", "expression")
add("SYN-EXPR-EXPR-STATEMENT-MISSING-SEMICOLON", ";")
add("SYN-EXPR-LEADING-DOUBLE-EQUAL", "==")
add("SYN-EXPR-LEADING-STAR-OPERATOR", "*")
add("SYN-EXPR-MISSING-RHS-ASSIGNMENT", "expression", names="x")
add("SYN-EXPR-TERNARY-MISSING-COLON", ":")
add("SYN-EXPR-TRAILING-LOGICAL-AND", "&&")
add("SYN-EXPR-TRIPLE-EQUAL", "===")
add("SYN-EXPR-UNBALANCED-OPEN-PAREN-CONSTRAINT", ")")
add("SYN-EXPR-UNMATCHED-CLOSE-PAREN", ")")


# =========================================================================
# B3 backfill (2026-09-13). Everything above predates it; everything below
# was authored in one pass over the classes that still had no metadata, from
# the case source and its `fix:`/`.ok.pss` control.
#
# Two rules the earlier sections imply but never state, both of which cost
# score here rather than earning it:
#
# * **One entity is declared alone.** `names:` reaches D3 = 3 only with two
#   or more, and the anchor asks for "both sides *and the relationship*". A
#   missing `;` after field `x` has one side. Declaring `x, A` to collect the
#   third point would be scoring, not measuring.
# * **A placement defect has two sides**, and gets both: the construct that is
#   in the wrong place and the scope that forbids it (`bins b0` in
#   `component C`). We currently name only the scope, so these score 2 -- the
#   gap is real and the case is where it should be recorded.
#
# Where a defect has no named entity at all -- a keyword used as a name, an
# anonymous `activity`, an operator run inside an expression -- `names:` is
# left off rather than filled with the nearest identifier to hand. 63 cases
# are in that position and their D3 is `null`, which is the correct answer.


# -- syntax.scope ---------------------------------------------------------
#
# "X is not allowed here." `cause:` is the construct keyword; whether the
# message also says *where* X would be legal is D4's question, not D1's.

add("SYN-SCOPE-ACTION-AT-FILE-SCOPE", "action", names="A")
add("SYN-SCOPE-ACTIVITY-AT-FILE-SCOPE", "activity")
add("SYN-SCOPE-BINS-OUTSIDE-COVERGROUP", "bins", names="b0, C")
add("SYN-SCOPE-COMPONENT-DECL-INSIDE-ACTION-BODY", "component", names="D, A")
add("SYN-SCOPE-COVERPOINT-OUTSIDE-COVERGROUP", "coverpoint", names="C")
add("SYN-SCOPE-FIELD-DECL-AT-FILE-SCOPE", "int", names="x")
add("SYN-SCOPE-IMPORT-INSIDE-STRUCT", "import", names="S")
add("SYN-SCOPE-PACKAGE-INSIDE-COMPONENT", "package", names="P, C")
add("SYN-SCOPE-POOL-AT-FILE-SCOPE", "pool", names="p_foo")
add("SYN-SCOPE-RAND-FIELD-AT-FILE-SCOPE", "rand", names="x")
add("SYN-SCOPE-STRUCT-DECL-INSIDE-EXEC-BODY", "struct", names="S")
add("SYN-SCOPE-TYPEDEF-INSIDE-ACTIVITY", "typedef", names="foo_t")


# -- syntax.stmt ----------------------------------------------------------
#
# Almost all punctuation: a statement keyword whose required `(`, `)` or `{`
# is absent. The term is the missing token, and no `names:` -- which
# identifiers surround a missing paren is an accident of the example.

add("SYN-STMT-BIND-MISSING-WITH-WRAPPER", "bind", names="A")
add("SYN-STMT-CONSTRAINT-IF-NO-PARENS", "(")
add("SYN-STMT-FOREACH-MISSING-COLON", ":")
add("SYN-STMT-FOREACH-NO-PARENS", "(")
add("SYN-STMT-IF-MISSING-PAREN-CLOSE", ")")
add("SYN-STMT-IF-NO-PARENS-ACTIVITY", "(")
add("SYN-STMT-PARALLEL-MISSING-OPEN-BRACE", "{")
add("SYN-STMT-REPEAT-COUNT-MISSING-PAREN", "(")
add("SYN-STMT-REPEAT-WHILE-MISSING-PAREN", "(")
add("SYN-STMT-SELECT-BODY-MISSING-CLOSE-BRACE", "select")
add("SYN-STMT-SELECT-NO-BRACES", "{")
add("SYN-STMT-WITH-MISSING-BRACES", "with")


# -- syntax.reserved / syntax.keyword -------------------------------------
#
# A keyword written where a name belongs, or a modifier PSS does not have.
# `cause:` is the offending keyword itself -- it is what the message must be
# about, and "expected identifier before 'action'" is an accurate diagnosis
# even though it never uses the word "reserved". `names:` is the enclosing
# declaration, because the thing the user was trying to name has no valid
# name to echo.

add("SYN-RESERVED-INT-ACTION-FIELD", "action", names="A")
add("SYN-RESERVED-KEYWORD-AS-ACTION-NAME", "component", names="C")
add("SYN-RESERVED-KEYWORD-AS-COMPONENT-NAME", "struct")
add("SYN-RESERVED-KEYWORD-AS-ENUM-NAME", "action")
add("SYN-RESERVED-KEYWORD-AS-FIELD-NAME-AND-TYPE-COLLISION", "int", names="C")
add("SYN-RESERVED-KEYWORD-AS-FUNCTION-NAME", "struct", names="C")
add("SYN-RESERVED-KEYWORD-AS-PACKAGE-NAME", "action")
add("SYN-RESERVED-KEYWORD-AS-TYPEDEF-NAME", "component")
add("SYN-RESERVED-KEYWORD-RAND-AS-VARIABLE-NAME", "rand", names="A")
add("SYN-RESERVED-STRUCT-NAMED-COMPONENT", "component")
add("SYN-RESERVED-UNEXPECTED-KEYWORD", "struct", names="E")

add("SYN-KEYWORD-CLASS-INSTEAD-OF-COMPONENT", "class", names="C")
add("SYN-KEYWORD-EXTENDS-FOR-INHERITANCE", "extends", names="C")
add("SYN-KEYWORD-FINAL-COMPONENT", "final", names="C")
add("SYN-KEYWORD-KEYWORD-AS-FIELD-NAME", "struct", names="S")
add("SYN-KEYWORD-NUMERIC-LITERAL-MISLABELED-KEYWORD", "123")
add("SYN-KEYWORD-RAND-STRUCT", "rand", names="S")
add("SYN-KEYWORD-RESERVED-WORD-AS-FUNCTION-NAME", "return")
add("SYN-KEYWORD-STATIC-ON-ACTION", "static", names="A")
add("SYN-KEYWORD-VIRTUAL-ACTION", "virtual", names="A")


# -- syntax.type ----------------------------------------------------------
#
# `bound` rather than "low bound" or "lower bound": the defect is which bound
# is wrong, and the term should not pick between two equally good spellings.
# The unterminated-generic cases name the *field* being declared, not the
# component around it -- the two sides are the type and the field.

add("SYN-TYPE-BIT-LOW-BOUND-NONZERO-ACTION", "bound", names="x")
add("SYN-TYPE-BIT-LOW-BOUND-NONZERO-STRUCT", "bound", names="x")
add("SYN-TYPE-ENUM-INVALID-BASE-TYPE-KEYWORD", "struct", names="E")
add("SYN-TYPE-ENUM-COMMA-01", r"\,")
add("SYN-TYPE-INHERIT-BASE-01", "identifier")
add("SYN-TYPE-INHERITANCE-MALFORMED-TEMPLATE-SPEC", ">", names="C")
add("SYN-TYPE-NESTED-UNTERMINATED-ANGLE-BRACKETS", ">", names="y")
add("SYN-TYPE-UNTERMINATED-GENERIC-FUNCTION-RETURN-TYPE", ">", names="foo")
add("SYN-TYPE-UNTERMINATED-TEMPLATE-ANGLE-FIELD", ">", names="x")


# -- syntax.lex -----------------------------------------------------------

add("SYN-LEX-BASED-LITERAL-BAD-DIGIT-MISCLASSIFIED", "digit", names="x")
add("SYN-LEX-KEYWORD-JARGON", "@")
add("SYN-LEX-STRAY-AT-SYMBOL-SILENT", "@")
add("SYN-LEX-STRAY-HASH-01", "#")
add("SYN-LEX-UNTERMINATED-STRING-CASCADES", "string", names="s")
add("SYN-LEX-UNTERMINATED-TRIPLE-QUOTE-BARE", "string", names="s")


# -- syntax.recover -------------------------------------------------------
#
# The defect is ordinary; the case is about what the parser does *after* it.
# So the terms are the ordinary ones, and a recovery that renames the defect
# to whatever it stopped on scores 1 -- which is the point of the class.

add("SYN-RECOVER-DEEP-INDEX-CHAIN-MISSING-SEMICOLON", ";")
add("SYN-RECOVER-DEEP-NESTED-FOREACH-MISSING-SEMICOLON", ";")
add("SYN-RECOVER-DEEP-NESTED-PARENS-MISSING-CLOSE", ")")
add("SYN-RECOVER-DEEP-NESTING-IF-DEPTH5-MISSING-SEMICOLON", ";")
add("SYN-RECOVER-PAIR-KEYWORD-FIELD-NAME-TWO-STRUCTS", "action", names="S")
add("SYN-RECOVER-PAIR-KEYWORD-FIELD-NAME-TWO-STRUCTS-2", "action", names="S")
add("SYN-RECOVER-PAIR-MISSING-SEMICOLON-TWO-ACTIONS", ";", names="x")
add("SYN-RECOVER-PAIR-MISSING-SEMICOLON-TWO-ACTIONS-2", ";", names="x")
add("SYN-RECOVER-WELL-FORMED-DECL-BEFORE-UNCLOSED-SECOND", "component",
    names="D")


# -- syntax.multifile -----------------------------------------------------
#
# `names:` is checked against the case source, so a case whose defect lives in
# a companion file gets none: the entity is not in the file being checked.

add("SYN-MULTIFILE-COMPANION-01", ";")
add("SYN-MULTIFILE-TWO-DEFECTS-01", ";")
add("SYN-MULTIFILE-FILE2-LINE1-01", "identifier")
add("SYN-MULTIFILE-ERROR-IN-FILE1-OF-2", ";", names="x")
add("SYN-MULTIFILE-FILE1-OF-3-01", ";")
add("SYN-MULTIFILE-ERROR-IN-FILE2-OF-3", ";", names="x")
add("SYN-MULTIFILE-ERROR-IN-FILE2-OF-4", "action", names="S")
add("SYN-MULTIFILE-ERROR-IN-FILE3-OF-3", ";", names="x")
add("SYN-MULTIFILE-UNCLOSED-FILE1-01", "component")


# -- syntax.template ------------------------------------------------------
#
# "mustache" is this corpus's word for `{{ }}` and appears in the case titles,
# so it is the users' vocabulary here rather than ours. `unterminated` is a
# second term only where being unterminated *is* the defect.

add("SYN-TEMPLATE-BLOCK-CLOSE-01", "endif")
add("SYN-TEMPLATE-MEMBER-01", "identifier")
add("SYN-TEMPLATE-MUSTACHE-LITERAL-BRACES-HINT", "mustache")
add("SYN-TEMPLATE-MUSTACHE-MALFORMED-EXPRESSION", "mustache")
add("SYN-TEMPLATE-MUSTACHE-UNTERMINATED-EXPRESSION", "mustache, unterminated")
add("SYN-TEMPLATE-TEMPLATE-COMMENT-UNTERMINATED", "comment, unterminated")
add("SYN-TEMPLATE-TEMPLATE-DIRECTIVE-MALFORMED", "(")
add("SYN-TEMPLATE-TEMPLATE-DIRECTIVE-UNTERMINATED", "directive, unterminated")


# -- syntax.volume --------------------------------------------------------
#
# `about: tool` cases (the four error-cap ones) get nothing: the diagnostic is
# about the tool's own reporting and has no construct to name, so any `cause:`
# would be grading our phrasing against itself.
#
# `SYN-VOLUME-LARGE-VOLUME-FIFTY-DEFECTS` is absent for a duller reason: at 60
# lines it is exactly on the validator's hard budget and cannot carry another
# header line. Its 20-defect sibling has the identical defect shape.

add("SYN-VOLUME-CAP-BOUNDARY-EXACT-COUNT", "identifier", names="S0")
add("SYN-VOLUME-CAP-DISABLED-ALL-REPORTED", "identifier", names="S0")
add("SYN-VOLUME-MANY-INDEPENDENT-MISSING-FIELD-NAMES", "identifier",
    names="S0")
add("SYN-VOLUME-THIRTY-01", names="a00")


# -- semantic -------------------------------------------------------------
#
# The template-arity pair names the *type* whose parameter list is wrong
# (`array`, `list`): "type accepts 2 template parameter(s)" does not say which
# type, and in a file with several instantiations that is the whole question.

add("SEM-COMPILE-COMPILE-IF-UNBRACED", "braces, deprecated")
add("SEM-COMPILE-COMPILE-IF-UNBRACED-CONTEXTS", "braces, deprecated")
add("SEM-COMPILE-COMPILE-IF-UNBRACED-ELSE", "braces, deprecated")

add("SEM-TEMPLATE-ARRAY-TEMPLATE-ARITY-EXTRA-ARG", "template parameter",
    names="array")
add("SEM-TEMPLATE-MISSING-TEMPLATE-ARG-DEFAULT", "template parameter",
    names="list")
