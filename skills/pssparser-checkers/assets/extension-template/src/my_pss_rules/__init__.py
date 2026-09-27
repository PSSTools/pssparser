"""my-pss-rules: a pssparser checker extension.

The whole contract with pssparser is ``register(reg)``, reached through the
``pssparser.extensions`` entry point in pyproject.toml.
"""

#: Minimum pssparser checker-API version this extension needs.  pssparser
#: reads it before calling register() and refuses the extension (PSS032)
#: if the running build is older.
REQUIRES_API = 1

__version__ = "0.1.0"


def register(reg) -> None:
    """Contribute this package's checkers to *reg* (an ExtensionRegistry)."""
    reg.version = __version__
    reg.description = "House lint rules for PSS"

    # Import rule modules here, not at module scope: a broken rule module is
    # then reported as PSS030 against this extension instead of breaking the
    # import of the package that declares the entry point.
    from .field_names import FieldNameLengthChecker

    reg.add_checker(FieldNameLengthChecker)
