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

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
