# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

project = 'pssparser'
copyright = '2024, Matthew Ballance'
author = 'Matthew Ballance'

project_dir=os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)))

# Prefer an *installed* pssparser over the source tree.
#
# autodoc has to import pssparser.ast and pssparser.core, which are compiled
# Cython extensions. They exist only in a built/installed package -- the source
# tree under python/ has the .pyx/.pxd inputs but no .so. Putting that tree
# first on sys.path therefore shadows a working install with one that cannot
# satisfy autodoc, and the API reference silently comes out empty (192 "failed
# to import" warnings, while the build still reports success).
#
# Fall back to the source tree only when nothing is installed, so that a docs
# build in a bare checkout still produces the narrative pages.
try:
    import pssparser.ast  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.join(project_dir, "python"))

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
]

# -- AST model reference (docs/ast/) -----------------------------------------
# Rendered from ast/*.yaml at docs-build time by pyastbuilder's Sphinx support
# (`pip install pyastbuilder[sphinx]`; diagrams also need Graphviz's `dot`).
# Without it, docs/_ext/astb_fallback.py keeps the build working and each AST
# reference page says what is missing. See docs/design/astbuilder-sphinx-plan.md.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ext"))
try:
    import astbuilder.sphinx  # noqa: F401
    import pss_rule_projection  # noqa: F401  (imports astbuilder.projection)
    extensions.append('astbuilder.sphinx')
except ImportError:
    extensions.append('astb_fallback')

astbuilder_models = {
    "pss": {
        "yaml": ["../ast/*.yaml"],
        "projections": [
            {"projection": "cpp", "namespace": "pssp::ast"},
            {"projection": "python", "module": "pssparser.ast"},
            "ts",
            "pss_rule_projection:RuleProjection",
        ],
        # Page order and titles; one page per ast/<group>.yaml (docs/ast/<group>.rst).
        "groups": [
            ("coretypes", "Scopes and core classes"),
            ("typescope", "Type declarations"),
            ("struct", "Structs and objects"),
            ("field", "Fields"),
            ("datatype", "Data types"),
            ("template", "Templates"),
            ("template_types", "Template parameters"),
            ("expr", "Expressions"),
            ("constraint", "Constraints"),
            ("activity", "Activities"),
            ("exec", "Exec blocks and procedural statements"),
            ("functions", "Functions"),
            ("coverage", "Coverage"),
            ("monitor", "Monitors"),
            ("extension", "Extensions"),
            ("override", "Overrides"),
            ("annotation", "Annotations"),
            ("linking", "Linker classes"),
        ],
        "roots": ["GlobalScope", "RootSymbolScope"],
        "phases": [
            ("parser", "set when the source is parsed"),
            ("linker", "set when the linker resolves names"),
        ],
        "doc_backticks": "literal",
        # Containment paths say little here: every scope holds
        # list<UP<ScopeChild>>, so the schema puts almost any class one step
        # below GlobalScope (finding F3 in docs/design/astbuilder-sphinx-plan.md).
        "paths": False,
    },
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
