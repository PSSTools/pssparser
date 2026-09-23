pss_rule_collection — example ``pssparser`` **extension**
==========================================================

A worked example of shipping a *collection* of checkers as one installable
package, using the ``pssparser.extensions`` entry point.  Read it together
with ``docs/checker_plugin_guide.rst``.

For the simpler case — one checker, one entry point — see
``examples/pss_naming_checker/`` instead.  Both mechanisms are supported; this
one exists because a package with a dozen rules should not need a dozen
entry-point lines, and because an extension needs somewhere to declare
package-level facts (its version, its API requirement) that a bare class
cannot carry.


What it does
------------

Two checkers, contributed by one extension named ``example-rules``:

+-------------------+--------+----------+------------------------------------------+
| Checker           | Code   | Severity | Meaning                                  |
+===================+========+==========+==========================================+
| component-naming  | PRC001 | warning  | ``component`` name is not PascalCase     |
+-------------------+--------+----------+------------------------------------------+
| package-naming    | PRC002 | warning  | ``package`` name is not lower_snake_case |
+-------------------+--------+----------+------------------------------------------+


Quick demo
----------

Install it (an editable install works well while developing)::

    pip install -e examples/pss_rule_collection/

Confirm it was picked up::

    pssparser --list-extensions

::

    Installed extensions (1):
      example-rules 0.1.0 [pss-rule-collection]
        Example rule collection: component and package naming
        checkers: component-naming, package-naming

Now just run the linter.  **No flags are needed** — installing an extension is
what makes its rules available::

    pssparser my_design.pss

To run only one of them, or to turn the collection off for a run::

    pssparser --checker component-naming my_design.pss
    pssparser --no-extensions my_design.pss


Project layout
--------------

::

    examples/pss_rule_collection/
    ├── README.rst              ← this file
    ├── setup.cfg               ← metadata + the single entry-point declaration
    ├── setup.py                ← minimal shim for editable installs
    ├── src/
    │   └── pss_rules/
    │       ├── __init__.py         ← register(): the whole contract
    │       ├── component_naming.py ← PRC001
    │       └── package_naming.py   ← PRC002
    └── tests/
        └── test_rule_collection.py


Key implementation notes
------------------------

**One entry point for the package** (``setup.cfg``)::

    [options.entry_points]
    pssparser.extensions =
        example-rules = pss_rules

The group must be ``pssparser.extensions``.  The key is the extension name
shown by ``--list-extensions``; the value is the module exposing
``register()``.

**The register function** (``src/pss_rules/__init__.py``)::

    REQUIRES_API = 1

    def register(reg):
        reg.version = "0.1.0"
        reg.description = "Example rule collection: component and package naming"
        from .component_naming import ComponentNamingChecker
        from .package_naming import PackageNamingChecker
        reg.add_checker(ComponentNamingChecker)
        reg.add_checker(PackageNamingChecker)

Three details worth copying:

1. **Import the rule modules inside** ``register()``, not at module scope.  A
   failure in one rule module is then reported as a ``PSS030`` against this
   extension, instead of breaking the import of the package that declares the
   entry point.

2. **Declare** ``REQUIRES_API`` **at module level.**  It lets pssparser refuse
   an incompatible extension before ``register()`` runs, which is the only
   point at which refusing is free of side effects.  The result is one clear
   ``PSS032`` message naming both versions, rather than an ``AttributeError``
   from inside a checker halfway through a run.

3. **Probe with** ``reg.api_version`` **for anything newer than**
   ``REQUIRES_API`` **promises.**  ``API_VERSION`` is bumped only for
   *incompatible* changes, so one release of an extension can support several
   releases of pssparser by guarding the newer paths.

**Choosing marker IDs.**  IDs are globally unique across the core and every
installed extension; a collision is a ``PSS033`` **error** and costs the
losing checker its registration.  Pick an unused prefix — three letters plus
three digits is the convention, ``PRC001`` here.  The ``PSS`` prefix is
reserved for the built-in core checker.

**The checker classes themselves** are ordinary ``CheckerBase`` subclasses,
identical to what a single-checker plug-in would contain.  Nothing about
writing a rule changes when it ships as part of a collection.


Running the tests
-----------------

From the repository root::

    PYTHONPATH=python python -m pytest examples/pss_rule_collection/tests -q
