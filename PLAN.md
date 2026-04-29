# pssparser: ivpm-build Migration & CI Plan

## Problem

1. `setup.py` imports `from ivpm.setup import setup` — this couples the build
   to the full `ivpm` runtime package.  `ivpm-build` was extracted specifically
   to break this dependency.
2. CI uses the deprecated `setup.py bdist_wheel` invocation.  Modern pip/setuptools
   emits warnings and will eventually drop support.
3. The Windows CI job is commented out and broken.
4. There is no `[build-system]` table in `pyproject.toml` (none exists), so
   pip falls back to legacy build isolation with unpredictable behaviour.
5. `setup_requires=['cython', 'ivpm']` pulls in the heavy `ivpm` package at
   build time just to get `ivpm.setup.setup`.

---

## Migration Path

This project uses **Path 1** (single import swap) with one minor addition: also
add `ivpm-build` to the build-system requirements.

### Step 1 — Add `pyproject.toml`

Create `pyproject.toml` with a `[build-system]` table:

```toml
[build-system]
requires = [
    "setuptools>=64",
    "wheel",
    "cython",
    "ivpm-build",
    "ivpm",            # still needed at build time for PkgInfoRgy queries
]
build-backend = "setuptools.build_meta"
```

### Step 2 — Update `setup.py` imports

Change one line in `setup.py`:

```python
# Before
from ivpm.setup import setup

# After
from ivpm_build.setup import setup
```

Update `setup_requires` to match `[build-system].requires`
(remove the redundancy or drop `setup_requires` entirely — it is ignored
when a `[build-system]` table is present):

```python
# Remove or keep for legacy pip compatibility:
setup_requires = ['cython', 'ivpm-build', 'ivpm']
```

### Step 3 — Verify locally

```bash
pip install ivpm-build
python -m build --wheel --no-isolation   # dry-run with local deps
```

---

## CI Fixes

### 3a — Replace `setup.py bdist_wheel` with `python -m build`

Old (all three jobs):
```yaml
- name: Build Python wheels
  run: |
    for py in cp39-cp39 cp310-cp310 cp311-cp311 cp312-cp312; do
      /opt/python/${py}/bin/python setup.py bdist_wheel
    done
```

New:
```yaml
- name: Build Python wheels
  run: |
    for py in cp39-cp39 cp310-cp310 cp311-cp311 cp312-cp312; do
      /opt/python/${py}/bin/python -m pip install build
      /opt/python/${py}/bin/python -m build --wheel --no-isolation
    done
```

`--no-isolation` is correct here because the manylinux job already
pre-installs all build deps in the loop above.

### 3b — Add `ivpm-build` to the pip install steps

In every job's "Install additional build dependencies" / "Install Packages" step,
add `ivpm-build` alongside `ivpm`:

```yaml
# Linux manylinux loop:
/opt/python/${py}/bin/python -m pip install ninja wheel cython setuptools ivpm ivpm-build

# macOS / Windows single-python:
python -m pip install ivpm ivpm-build twine cython ninja wheel cmake
```

### 3c — Re-enable Windows CI

The Windows job is commented out.  Issues to fix before re-enabling:

| Issue | Fix |
|---|---|
| `cmake .. -GNinja` may fail without explicit Ninja path | Add `ninja` to PATH via `pip install ninja` (already done) |
| `setup.py bdist_wheel` → replace with `python -m build --wheel --no-isolation` | See 3a |
| DLL install path: `pssparser.dll` must land in `build/lib/` | Already fixed in CMake (`CMAKE_INSTALL_BINDIR=lib`), verify |
| `auditwheel` not available on Windows | Remove auditwheel step from Windows job |

Uncomment the `ci-win32` job once the above are confirmed working locally.

### 3d — Audit Wheels step (Linux)

The current logic is fragile:

```yaml
for whl in dist/*.whl; do
  [ -f "$whl" ] || break   # BUG: should be 'continue', not 'break'
  ...
```

Fix the guard:

```yaml
for whl in dist/*.whl; do
  [ -f "$whl" ] || continue
  /opt/python/cp39-cp39/bin/auditwheel repair "$whl"
  rm "$whl"
done
```

### 3e — Unit / integration test step (missing)

The CI has no Python unit-test step.  Add after wheel build:

```yaml
- name: Run Python tests
  run: |
    /opt/python/cp312-cp312/bin/python -m pip install pytest dist/*cp312*.whl
    /opt/python/cp312-cp312/bin/python -m pytest tests/python -v --tb=short
```

---

## Implementation Order

1. Create `pyproject.toml` (Step 1)
2. One-line `setup.py` change (Step 2)
3. Update CI: fix `bdist_wheel` → `python -m build`, add `ivpm-build`, fix
   auditwheel guard (Steps 3a–3d)
4. Add Python test step to CI (Step 3e)
5. Verify CI passes on Linux and macOS
6. Re-enable Windows job (Step 3c)

---

## Open Questions / Deferred

- **`ivpm` still needed at build time**: `PkgInfoRgy` queries in `setup.py`
  (via `ivpm_extdep_pkgs`) still require `ivpm` at build time.  This can be
  eliminated in a later step by switching to Path 3 (pure `pyproject.toml` +
  `[tool.ivpm-build]`), but that requires more invasive changes.
- **Windows CI**: Leave commented out until Linux/macOS are confirmed green;
  then address DLL path issues separately.
- **`setup.py bdist_wheel` deprecation warning**: Replacing with `python -m build`
  is sufficient; no change to the `setup.py` content is needed.
