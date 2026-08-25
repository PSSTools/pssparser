#############
AST Structure 
#############

The PSS language is object-oriented, with some aspect-oriented features as well.
The AST structure reflects this by maintaining both a logical and a physcial 
view of the content.

Performing syntax parsing on a file results in a physcial AST structure, 
which is captured in an object of type `pssp::ast::IGlobalScope`. There 
is a 1:1 relationship between file and `IGlobalScope` object.

A "Symbol Tree" is built as part of the symbol resolution process. This 
tree represents the logical view of the content. Specifically, all
content within the same namespace is visible within a single "Symbol"
scope, with pointers back to the physical view. In general a "Symbol"
type exists for any scope that supports multiple contributors -- 
For example, package, action, component, function. Scopes, such as
constraints, that do not support contribution from multiple sources
are represented only in the "physical" view of the AST and not 
within the logical "Symbol Tree".

Let's look at an example.

.. code:: pss

    component pss_top {
        action Entry { }
    }


.. code:: pss

    extend component pss_top {
        action B { }
    }

In this case, the RootSymbolTree will be structured as follows:

* RootSymbolTree
    * children
        * pss_top : SymbolTypeScope
            * children
                * Entry : SymbolTypeScope
                * B : SymbolTypeScope
    * units
        * pss_top.pss : GlobalScope
            * children
                * pss_top : Component
                    * children
                        * Entry : Action
        * pss_top_ext.pss : GlobalScope
            * children
                * pss_top : ExtendType
                    * children
                        * B : Action


Note how the children of the symbol tree hold the 'merged' view of the
PSS content that takes type extension into account. Meanwhile, the
physical view of the PSS content is maintained under the 'units'
subsection of the symbol tree.

Scopes that are not in the Symbol Tree
--------------------------------------

Not every ``SymbolScope`` belongs in the Symbol Tree, and the template-string
nodes (``TemplateString``, ``TemplateElem`` and its block subclasses -- see
:ref:`template-strings`) are the clearest case.

They derive from ``SymbolScope`` because they hold declarations: a
``{% foreach (it : c) %}`` directive introduces ``it`` for the duration of its
block, and the name-resolution machinery only accepts an ``ISymbolScope`` on
its scope stack.  But they are deliberately **not** hoisted into the Symbol
Tree, because a template is not a scope multiple sources contribute to -- and
hoisting them made every diagnostic inside a template appear three times, once
per parent the node acquired.

The consequence to know about: a ``SymbolRefPath`` is a chain of child indices
read from the Symbol Tree, so a reference to a template-local variable records
a path that cannot address its declaration.  Resolution during the walk is
correct -- the scope is on the stack -- but following the recorded path
afterwards lands somewhere unrelated.  See ``docs/design/known-issues.md``
P5-X2.

