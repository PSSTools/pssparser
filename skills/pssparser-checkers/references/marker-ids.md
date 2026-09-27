# Choosing marker IDs, severities, and text

Every diagnostic a checker emits carries an ID from its `marker_defs`. Users
treat IDs as an interface: they write them in `-Werror=ID`, in `[severity]`
tables, in CI scripts, and in bug reports. Choose them once and keep them.

## The ID

- **Shape:** three uppercase letters plus three digits, e.g. `MPR001`. This is
  a convention, not enforced, but every tool that reads IDs (including the
  `--stats` histogram and users' regexes) assumes it.
- **Prefix:** one prefix per extension (or per organization), used by no one
  else. Never `PSS`: pssparser owns that prefix and keeps adding IDs in it.
- **Numbering:** allocate sequentially from `001`. Never reuse a number after
  retiring a rule; leave the gap.

Check what is already taken in the environment you target:

```bash
pssparser --list-markers
pssparser --list-markers | grep '^MPR'
```

Uniqueness is enforced at load time, per ID:

- An installed extension whose checker declares an ID already owned (by the
  core or by an extension loaded earlier) gets `PSS033`, an **error**, and
  that checker is not registered. The rest of the extension still loads.
- `--load-checker` with a clashing ID stops the run with exit code 2 and
  `error: Duplicate MarkerDef ID`.

A `PSS` ID in an extension may work today and break after a pssparser
upgrade that allocates the same number: the core registers first, so your
checker is the one dropped.

A test that catches a clash before your users do (from the template):

```python
from pssparser.checkers import CheckerManager, MarkerDef

OURS = [MarkerDef(id="MPR001", severity="warning", summary="example")]

m = CheckerManager()
m.discover(load_extensions=False)          # the core's IDs only
taken = {d["id"] for d in m.list_all_markers()}
assert not taken & {md.id for md in OURS}
assert not any(md.id.startswith("PSS") for md in OURS)
```

## One ID per problem, not per message

Give an ID to each distinct problem a user may want to promote, demote, or
silence independently. Two rules that users will always configure together
can share an ID; a rule users may want off while keeping its neighbor needs
its own. Put variable detail (names, numbers) in the message, never in the ID.

## Severity

`MarkerDef.severity` is the default; users can override it for any ID in
`.pssparser.toml`:

```toml
[severity]
MPR001 = "error"      # error | warning | info | hint | off
```

| Default | Use for | Effect |
|---|---|---|
| `error` | The model is wrong or will misbehave in a tool. | Exit code 1. |
| `warning` | Probably a mistake, or a firm house rule. | Reported; exit 0 unless `-Werror`. |
| `info` | Style advice. | Reported; never fails a run. |
| `hint` | Low-value suggestions, e.g. for editor integrations. | Reported; never fails a run. |

Prefer `warning` for lint rules and let users promote with `-Werror` or
`[severity]`. An `error` default forces every user to write configuration to
adopt your extension incrementally.

`add_marker(severity=...)` overrides the default for one occurrence. Use it
sparingly, e.g. when one ID covers a family of cases of different
seriousness. `--describe` and `--list-markers` show only the default.

## `summary` and `detail`

- `summary`: one line, a noun phrase describing the problem ("Field name is
  shorter than the configured minimum"). No trailing period. It appears in
  `--list-markers` and `--describe-checker`.
- `detail`: what is wrong, why it matters, and **how to fix it**, including
  any options that change the rule. `pssparser --describe ID` prints it
  verbatim.
- The per-occurrence `message` in `add_marker` names the specific thing:
  "field 'n' is shorter than 2 characters". pssparser adds the `[ID]` prefix.

Confirm the result reads well:

```bash
pssparser --describe MPR001
pssparser --describe-checker field-name-length
```
