# The standard library

pssparser compiles the PSS core-library packages (LRM Annex C) into itself and
loads them into every `Parser` as fileid 0. You never pass them to `parse()`.

## Packages are imported explicitly

None of them is visible to user code until the code imports it:

| Package | Declares (highlights) |
|---|---|
| `std_pkg` | `message`, `error`, `fatal`, `format_string`, `message_verbosity_e`, `endianness_e`, `packed_s`, `sizeof_s`, file handles, `float_base_s`, the `doc` and `code_doc` annotations |
| `executor_pkg` | `executor_c`, `executor_group_c`, `executor_base_c`, `executor_trait_s`, `executor_claim_s`, `executor()` |
| `addr_reg_pkg` | `addr_handle_t`, address spaces (`contiguous_addr_space_c`, `transparent_addr_space_c`), regions, claims (`addr_claim_s`, `transparent_addr_claim_s`), register types |
| `sync_pkg` | `channel_c` |

```pss
import std_pkg::*;
import addr_reg_pkg::*;
component pss_top {
    addr_handle_t h;
    action run {
        exec body { message(LOW, "hello"); }
    }
}
```

If the import is missing, `link()` raises, and the message names the package
to import: `unknown identifier 'message'; declared in std_pkg -- add 'import
std_pkg::*;'`. Before you conclude that a model is broken, check your own
generated or test PSS for that line.

`refs.occurrences()` reports names bound to these packages with resolution
`library`, and their `decl_location.fileid` is 0.

## Reading the sources

A tool that documents or cross-references the core library needs its `.pss`
text:

```python
import os
import pssparser

print(pssparser.get_stdlib_dir())
for path in pssparser.get_stdlib_files():       # sorted; [] if absent
    with open(path) as f:
        first = f.readline().strip()
    print(os.path.basename(path), "--", first)
```

`get_stdlib_files()` returns an empty list, and does not raise, when the
directory is missing. Treat that as "no core-library reference available".

Use these files for display and cross-reference only. Do not pass them to
`Parser.parse()`: the parser already contains them, so they would be declared
twice.
