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

