# Rule files (`pss-rules`)

A rule file declares lint rules in YAML, with each condition written as a CEL
expression over the syntax tree. pssparser's C++ core loads it, so one file
works in the command line, in CI, and in the TypeScript/WASM build that editor
integrations use. This is the first choice for a house rule. Write a Python
checker only for what a rule file cannot express (see `SKILL.md`).

User documentation, which covers the same ground in more detail:
<https://psstools.github.io/pssparser/lint-rule-authoring.html>.

## The loop

1. Write the rule and its `examples:` (a model that must report, and a near
   miss that must not).
2. `pssparser --check-rules acme.yaml`. It loads the file, type-checks every
   expression and runs every example. Exit 0 means clean.
3. Read each diagnostic: it gives the line and column *in the YAML file*.
   Fix, and repeat step 2.
4. Run the rule on a real model:
   `pssparser --rules acme.yaml --select ACME model.pss`.
5. Before writing a new PSS file, ask which rules it will get:
   `pssparser --rules-for ip/dma/new_block.pss` (add `--format json` for
   each rule's doc, options and examples). Nothing is parsed, and the file
   need not exist. Then `--explain ID` for any rule you don't know.

Without `--select`, a site's rules do not run: the default profile enables
none of them. A rule selected by ID, name or namespace shows its `style`
hints; one enabled only by a tier or profile has them hidden (the run says
`(1 hint hidden)`) until `--show-hints`.

## The file

```yaml
pss-rules:
  defaults: { tier: style, family: naming }
  rules:
    - id: ACME001
      name: component-name-suffix
      summary: A component's name doesn't end in the house suffix
      message: "component '${node.name.id}' should end in '${options.suffix}'"
      match: { kind: Component }
      options:
        suffix: { type: string, default: "_c", help: "Required suffix" }
      where: >-
        node.name.id != "pss_top" && !node.name.id.endsWith(options.suffix)
      examples:
        - code: |
            component dma { }                 // expect: ACME001
        - name: pss_top is exempt
          code: |
            component pss_top { }
        - name: suffixed
          code: |
            component dma_c { }
```

The fields:

| Field | Meaning |
|---|---|
| `id` | 2–5 capital letters, an optional team qualifier after a hyphen, then 3 digits: `ACME001`, `ACME-NET001`. `PSS`, `PSSP`, `PSSX` and `LINT` are reserved |
| `name` | Unique kebab-case. Works anywhere an ID does |
| `tier` | `correctness`, `suspicious`, `portability`, `simplify`, `style`, `pedantic`, `restriction` or `nursery`. Sets the default severity: `style` is a hint |
| `summary`, `message` | One line each. `${expr}` interpolates; `$${` is a literal `${` |
| `match` | `kind` (one or a list; subclasses match), optional `inside` / `not_inside` an ancestor kind, each bounded by `stop` |
| `where` | A bool expression on `node`. Must be true for a finding |
| `let` | Named expressions, evaluated in order, usable in `where`, `report` and `message` |
| `report` | A list of nodes to report at, instead of `node` |
| `options` | `type` (`string`, `int`, `bool`, `string-list`), `default`, `help`. Read as `options.<name>` |
| `define` | Helper expressions, `name(param)`: a map of signature to expression |
| `examples` | `code:` (one file) or `files:` (a map of name to text) |

A named declaration (an action, component, field or enum) is reported at its
name, not across its body. You never need `report: "[node.name]"`.

## A rule that reads the linked model

An address or executor claim in an action that is not `rand`:

```yaml
pss-rules:
  defaults: { family: decl, tier: suspicious }
  rules:
    - id: ACME002
      name: claim-not-rand
      summary: An address or executor claim is not declared 'rand'
      message: "claim '${node.name.id}' is not 'rand', so it is not allocated as written"
      match: { kind: Field, inside: { kind: Action } }
      let:
        t: type_decl(node.type)
      where: >-
        !has_flag(node.attr, FieldAttr.Rand) && t.hasValue() &&
        (derives_from(t.value(), "addr_reg_pkg::addr_claim_base_s") ||
         derives_from(t.value(), "executor_pkg::executor_claim_s"))
      examples:
        - code: |
            import addr_reg_pkg::*;
            component pss_top {
              transparent_addr_space_c<> mem;
              action my_action {
                transparent_addr_claim_s<> claim;     // expect: ACME002
              }
            }
        - name: a rand claim, and a user type derived from a claim
          code: |
            import addr_reg_pkg::*;
            component pss_top {
              transparent_addr_space_c<> mem;
              struct my_claim_s : addr_claim_s<> { }
              action my_action {
                rand transparent_addr_claim_s<> c1;
                my_claim_s c2;                        // expect: ACME002
              }
            }
```

- `type_decl(node.type)` gives the declaration a field's type names. It
  follows typedefs, and for `S<4>` it gives that specialization. It is
  optional: `.hasValue()` and `.value()`, or `.orValue(x)`.
- `derives_from(t, "pkg::name")` includes `t` itself. A generic template's
  name, with no `<...>`, matches every specialization of it.
- `type_named("pkg::name")` gives a type by name; `"::name"` is the global
  package.
- A literal type name is checked when the file loads. A name the model does
  not have gives none or `false` at run time, plus a `PSSP223` note.

## Finding the right kinds, fields and functions

- **Node kinds and their fields:** the AST model reference,
  <https://psstools.github.io/pssparser/ast/index.html>, generated from
  `ast/*.yaml` (`docs/ast/` in the source; start from
  <https://psstools.github.io/pssparser/lint-nodes.html>). Every class, its
  base and subclasses, its fields with what they mean, and the enums; the
  "Lint rule" column of each class's "In each API" table gives the rule's
  spelling and type of each field. A field declared on a base is readable on
  every subclass: `Field.name` comes from `NamedScopeChild`.
- **Functions and operators:**
  <https://psstools.github.io/pssparser/lint-functions.html>
  (`docs/lint-functions.rst`).
- **A wrong guess is cheap.** `--check-rules` reports, for example,
  `type 'Field' has no field 'nme', nor does any class derived from it`, at
  the column of the typo.

Kinds and fields you will use often:

| You want | Write |
|---|---|
| A declaration's name | `node.name.id` |
| Action / component / struct | `match: { kind: Action }` (`Component`, `Struct`, `TypeScope` for any type) |
| A field and its type | `Field`, `node.type`, `type_decl(node.type)` |
| `rand`, `const`, `static`, ... | `has_flag(node.attr, FieldAttr.Rand)` |
| A type's base | `node.super_t`, `resolves_to(node.super_t)` |
| Where a node is | `enclosing(node, Action)`, `parent(node)`, `ancestors(node)` |
| What a reference names | `resolves_to(r)`, `decl_path(d)` |
| Every use of a declaration | `refs(d)`, `is_read(r)`, `is_written(r)` |
| A constant's value | `const_int(e)`, `const_bool(e)` (optional) |
| `select` / `match` / `if` branches | `branches(n)`, `ranges(n)` |
| Is it the user's code | `is_owned(n)`, `in_library(n)` |

## Pitfalls

- **A leading `!` is a YAML tag.** `where: !node.x` fails with `PSSP218`.
  Write expressions as block scalars (`where: >-`) or quoted strings. That
  also protects `:`, `#` and `?`.
- **An unset field is `null`.** Reading through it is an error at run time
  (`PSSP220`), and the rule then stops for that file.
  `node.super_t.elems` on an action with no base fails. Guard the read with
  `has(node.super_t)`, or use `node.?super_t`.
- **Flags are not numbers.** `int(node.attr)`, `node.attr % 8` or
  `node.attr > 3` is a load error. Use `has_flag`. A plain enum is compared
  with `==`: `node.op == ExprBinOp.BinOp_Eq`.
- **The tree is the source as written.** An `extend`'s members belong to the
  `extend`. Nodes the linker adds, such as each action's `comp` handle, are
  not in it.
- **Rules run only on a clean model.** If the model has parse or link
  errors, no rule runs, and a `PSSP230` note says so.
- **Examples are whole models.** Give each one a component scope. Add
  `import std_pkg::*;`, `import addr_reg_pkg::*;` or `import executor_pkg::*;`
  for library types. An example runs alone, with the rule's default options.

## Examples (`// expect:`)

- `// expect: ACME001` on a line expects one finding of the rule on that
  line. `// expect: ACME001 @ 4:17` gives the position, counted in the
  example's own text. List several with commas; `/* expect: ID */` also
  works.
- An example with no `expect`, or with `// expect: none`, must report
  nothing. Always include at least one: the near miss shows what the rule
  leaves alone.
- A missing or extra finding is a `PSSP222` error at the example, saying what
  was expected where.

## Diagnostics while writing

| ID | Means |
|---|---|
| `PSSP210` | Not a rule file (no `pss-rules`, no `rules` list) |
| `PSSP211` | Unknown key |
| `PSSP212` | A field missing or of the wrong type; a malformed ID or example |
| `PSSP213` | Unknown node kind in `match:` |
| `PSSP214` | The expression does not parse |
| `PSSP215` | The expression does not type-check: an unknown field, function or option, or the wrong type |
| `PSSP216` | Too deeply nested, a recursive `define`, or a bad regex |
| `PSSP217` | Reserved or duplicate ID or name |
| `PSSP218` | YAML error, including a leading `!` |
| `PSSP220` / `PSSP221` | The rule failed at run time / ran out of evaluation budget |
| `PSSP222` | An example gave the wrong findings |
| `PSSP223` | The rule names a type the model does not have |

`pssparser --explain PSSP215` explains any of them.

## Using the rules

```toml
# .pssparser.toml
[lint]
rules  = ["lint/rules/"]      # files or directories, relative to this file
select = ["ACME"]             # an ID, name, namespace, tier or family:NAME

[lint.rule.component-name-suffix]
suffix = "_comp"
```

`pssparser --explain component-name-suffix` prints a loaded rule, including
the file and line it comes from. For CI on a rules repository, run
`pssparser --check-rules --format github lint/rules/`.
