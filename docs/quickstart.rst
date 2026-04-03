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



