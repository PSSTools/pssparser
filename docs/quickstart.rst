##########
Quickstart
##########

Installing pssparser
========================

pssparser is most easily installed as a Python 
package from PyPI. To install, run the following command:

.. code:: bash

   %  pip install pssparser

.. note:: 
    
    Add instructions for building from source.

Trying pssparser
====================

pssparser provides the `Parser` utility class to simplify
the process of parsing and linking PSS content from a Python script.

.. code:: Python
    
   from pssparser import Parser

   parser = Parser()
   parser.parses([(
    "file1.pss",
    """
    component pss_top {
      action A { }
    }
    """)
   ])

   root = parser.link()

The above snippet is incredibly simple, but shows the basic flow of
parsing and linking PSS content. 

- The `parses` method accepts a list of tuples, each containing a filename
  and the content to parse. The `parses` method raises an exception if 
  syntax errors are encountered in any file,
- The `link` method resolves references between the files and returns 
  a linked symbol tree for further processing.




Configuring the checks
======================

Running the CLI over a file needs no configuration at all::

   pssparser model.pss

When you want the same rules every time — in your editor, in CI, and for
everyone on the project — put them in a ``.pssparser.toml`` at the root of
the repository:

.. code-block:: toml

   # .pssparser.toml
   [warnings]
   error = true              # warnings fail the build

   [severity]
   PSS110 = "off"            # ...except this one

pssparser searches upward from the working directory, so the file applies
from anywhere in the tree.  To see exactly what is in effect and where each
value came from::

   pssparser --show-config

The full schema — checker selection, per-checker options, and the
precedence rules — is in :doc:`cli`.
