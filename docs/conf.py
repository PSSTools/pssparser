# Configuration file for the Sphinx documentation builder.
import os
import sys

# -- Project information -----------------------------------------------------
project = 'pssparser'
copyright = '2024, Matthew Ballance and Contributors'
author = 'Matthew Ballance'
release = '0.0.1'

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_dir, "python"))

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx_copybutton',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Napoleon settings (Google/NumPy docstring support)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# Intersphinx: link to Python stdlib docs
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

todo_include_todos = True

# -- Register 'pss' as a lexer alias (PSS syntax is close enough to C++ for
#    basic highlighting; avoids "Pygments lexer name 'pss' is not known" warnings)
from pygments.lexers import get_lexer_by_name
from sphinx.highlighting import lexers
try:
    lexers['pss'] = get_lexer_by_name('cpp')
except Exception:
    pass

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
    'collapse_navigation': False,
}
html_static_path = ['_static']
html_css_files = []

# -- Options for copybutton --------------------------------------------------
copybutton_prompt_text = r">>> |\.\.\. |\$ |% "
copybutton_prompt_is_regexp = True
