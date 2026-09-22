PSS 3.1 Core Library
====================

pssparser ships the four built-in core-library packages and loads them into
every parse, so no ``-y`` path or include is needed to use them. They live in
``src/stdlib/*.pss`` and are embedded into the parser binary at build time by
``src/stdlib/mk_pssstdlib.py``.

* ``std_pkg`` — string formatting and output, file operations, error
  reporting, randomization, floating point, standard annotations
* ``executor_pkg`` — execution contexts and target execution units
* ``addr_reg_pkg`` — address spaces, memory access, register model
* ``sync_pkg`` — synchronization and communication

.. note::

   The contents follow **Annex C** of the PSS 3.1 Public Review Draft, which
   is normative and states that it takes precedence over core-library material
   shown anywhere else in the standard — including the Syntax boxes in Clause
   21. Where this page and a Clause 21 Syntax box disagree, Annex C (and
   therefore pssparser) follows the annex.

Importing
---------

Conforming PSS imports what it uses:

.. code-block:: pss

    import std_pkg::*;
    import addr_reg_pkg::*;

    component c {
        exec init_up {
            print("starting\n");
        }
    }

None of the four packages is implicitly visible. Clause 21 gives the core
library no special visibility, and the one sentence that reads otherwise —
"example code may omit importing core library packages for brevity" — is about
the document's own examples, not about what a tool shall accept.

Omitting the import is an ordinary resolution failure, with a diagnostic that
names the import to add rather than claiming the name does not exist:

.. code-block:: text

    t.pss:2:9: error: unknown identifier 'print'; declared in std_pkg -- add 'import std_pkg::*;'

The same form appears for a type (``unknown type 'packed_s'; ...``) and for a
standard annotation, where it stays a warning because §7.13 requires an
unrecognized annotation to be disregarded rather than to fail the build.

Import is not re-export. ``addr_reg_pkg`` imports ``std_pkg`` for its own
declarations, but a model that writes ``import addr_reg_pkg::*;`` and then
uses ``packed_s`` or ``sizeof_s`` still needs ``import std_pkg::*;`` of its
own.

.. note::

   Before 2026-09-22 this implementation made ``std_pkg`` — and only
   ``std_pkg`` — visible from the root scope with no import, a non-portable
   superset of the standard. See :doc:`pss31_migration`.

``std_pkg``
-----------

String formatting and output (21.1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    solve pure function string format(string format_str, type... args);
    solve function void print(string format_str, type... args);

    enum message_verbosity_e {NONE, LOW, MEDIUM, HIGH, FULL};
    function void message(message_verbosity_e vrb_level,
                          string format_str, type... args);

``format`` and ``print`` are **solve-platform only**; ``message`` is the
facility for target exec blocks. See :ref:`stdlib-qualifiers` — the parser
does not yet enforce this.

File operations (21.2)
~~~~~~~~~~~~~~~~~~~~~~

All solve-platform only.

.. code-block:: pss

    typedef chandle file_handle_t;
    static const file_handle_t nullfilehandle = /* implementation-specific */;

    enum file_option_e {TRUNCATE, APPEND, READ};

    solve function file_handle_t file_open(string filename, file_option_e opt);
    solve function void         file_close(file_handle_t file_handle);
    solve function bool         file_exists(string filename);
    solve function void         file_write(file_handle_t file_handle,
                                           string format_str, type... args);
    solve function string       file_read(file_handle_t file_handle, int size = -1);
    solve function void         file_write_lines(string filename,
                                                 list<string> lines,
                                                 file_option_e opt);
    solve function list<string> file_read_lines(string filename);

Error reporting (21.3)
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    function void error(string format_str, type... args);
    function void fatal(int status, string format_str, type... args);

Neither is ``solve``- or ``target``-qualified, so both are callable from
either platform.

Randomization (21.4)
~~~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    function bit[32] urandom();
    function bit[32] urandom_range(bit[32] min, bit[32] max);

Floating point (21.5)
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    struct float_base_s <int Wm, int We, endianness_e E=LITTLE_ENDIAN>
        : packed_s<E> {
        rand bit[Wm] mantissa;
        rand bit[We] exponent;
        rand bit     sign;
    }

    typedef float_base_s<23, 8> float32_s;
    typedef float_base_s<52,11> float64_s;

Twenty-two ``pure function float64`` math functions are declared: ``log``,
``log10``, ``exp``, ``sqrt``, ``pow`` (two arguments), ``round``, ``floor``,
``ceil``, ``sin``, ``cos``, ``tan``, ``asin``, ``acos``, ``atan``, ``atan2``
(two), ``hypot`` (two), ``sinh``, ``cosh``, ``tanh``, ``asinh``, ``acosh``,
``atanh``; plus the decomposition set:

.. code-block:: pss

    pure function bit[52] float_mantissa(float64 fv);
    pure function bit[11] float_exponent(float64 fv);
    pure function bit     float_sign(float64 fv);
    pure function float64 to_float(bit[52] mantissa, bit[11] exp, bit sign);

.. warning::

   These declarations parse and link, but a consumer reading a ``float64``
   field out of the AST still gets a null-typed field: the Python AST builder
   has no ``DataTypeFloat``. See ``P1-G2a`` in
   ``docs/design/known-issues.md``.

Annotations (21.6)
~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    annotation code_doc { string text; }
    annotation doc      { string text; }

Core data types
~~~~~~~~~~~~~~~

.. code-block:: pss

    enum endianness_e {LITTLE_ENDIAN, BIG_ENDIAN};
    struct packed_s<endianness_e e = LITTLE_ENDIAN> {};
    struct sizeof_s<type T> {
        static const int nbytes = /* implementation-specific */;
        static const int nbits  = /* implementation-specific */;
    };

``sizeof_s`` is declared in ``std_pkg`` per 21.13.2. ``addr_reg_pkg`` imports
``std_pkg``, which is what makes it reachable through
``import addr_reg_pkg::*;`` as PSS 2.0 code expects.

``executor_pkg``
----------------

.. code-block:: pss

    struct executor_trait_s {};
    struct empty_executor_trait_s : executor_trait_s {};

    enum target_language_e {C, CPP, SV};

    component target_execution_unit_c {
        solve function void              set_filename(string filename);
        solve function string            get_filename();
        solve function void              set_target_language(target_language_e lang);
        solve function target_language_e get_target_language();
    }

    component executor_base_c {
        target function chandle get_context();
        solve function void set_target_execution_unit(
            ref target_execution_unit_c target_execution_unit);
        solve function ref target_execution_unit_c get_target_execution_unit();
    }

    component executor_c<struct TRAIT : executor_trait_s = empty_executor_trait_s>
        : executor_base_c { TRAIT trait; };

    component executor_group_c<struct TRAIT : executor_trait_s = empty_executor_trait_s> {
        solve function void add_executor(ref executor_c<TRAIT> exe);
    };

    struct executor_claim_s<struct TRAIT : executor_trait_s = empty_executor_trait_s> {
        rand TRAIT trait;
    };

    function ref executor_base_c executor();
    function void set_executor(ref executor_base_c xtr);

``get_context()`` is what a PSS ``export`` function's foreign-language
realization uses to identify the executor context it is running in; the first
parameter of that realization is the context handle (Annex D.1.1).

``set_executor`` is called from a component's ``exec init_up`` or
``init_down`` to assign its executor (21.7.2.6). A component that assigns none
inherits its parent's.

``addr_reg_pkg``
----------------

Address spaces and regions
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    typedef chandle addr_handle_t;
    const addr_handle_t nullhandle = /* implementation-specific */;

    component addr_space_base_c {};
    struct addr_trait_s {};
    struct empty_addr_trait_s : addr_trait_s {};

    component contiguous_addr_space_c<struct TRAIT : addr_trait_s = empty_addr_trait_s>
        : addr_space_base_c {
        solve function addr_handle_t add_region(addr_region_s<TRAIT> r);
        solve function addr_handle_t add_nonallocatable_region(addr_region_s<> r);
        bool byte_addressable = true;
    };

Note that ``add_nonallocatable_region`` takes ``addr_region_s<>``, not
``addr_region_s<TRAIT>``: a non-allocatable region carries no trait
constraint. ``addr_region_base_s`` carries ``bit[64] size`` and
``string tag``; ``get_tag(addr_handle_t)`` reads the tag back from a handle.

Claims and allocation modes (21.11)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: pss

    enum alloc_access_mode_e {EXCLUSIVE, SHARED};
    enum alloc_share_mode_e  {RANDOM, OVERLAP, SAME_ADDRESS};
    enum alloc_skip_mode_e   {DONT_SKIP, SKIP};

    struct alloc_base_mode_s {
        rand alloc_access_mode_e access;   constraint default access   == EXCLUSIVE;
        rand alloc_share_mode_e  sharing;  constraint default sharing  == RANDOM;
        rand alloc_skip_mode_e   skipping; constraint default skipping == DONT_SKIP;
        rand int                 tag;      constraint default tag      == -1;
    };

    struct addr_claim_s<struct TRAIT : addr_trait_s = empty_addr_trait_s,
                        struct ALLOC_MODE : alloc_base_mode_s = alloc_base_mode_s>
        : addr_claim_base_s {
        rand TRAIT       trait;
        rand bit[64] in [/* powers of two */] alignment;
        rand ALLOC_MODE  alloc_mode;
    };

Both parameters are defaulted, so ``addr_claim_s<my_trait_s>`` works
unchanged. ``ALLOC_MODE`` exists so that a user may derive from
``alloc_base_mode_s`` and add tool- or project-specific allocation attributes.

Memory access (21.13)
~~~~~~~~~~~~~~~~~~~~~

Every access function takes a trailing, defaulted memory-access descriptor:

.. code-block:: pss

    struct mem_access_desc_s {}       // empty by design -- extend it

    target function bit[64] addr_value(addr_handle_t hndl,
                                       mem_access_desc_s mem_access_desc = {});
    solve  function bit[64] addr_value_solve(addr_handle_t hndl,
                                       mem_access_desc_s mem_access_desc = {});
    solve  function bool    addr_value_abs(addr_handle_t hndl,
                                       mem_access_desc_s mem_access_desc = {});

    target function bit[N]  read8/read16/read32/read64(addr_handle_t hndl,
                                       mem_access_desc_s mem_access_desc = {});
    target function void    write8/write16/write32/write64(addr_handle_t hndl,
                                       bit[N] data,
                                       mem_access_desc_s mem_access_desc = {});
    target function void    read_bytes(addr_handle_t hndl, list<bit[8]> data,
                                       int size,
                                       mem_access_desc_s mem_access_desc = {});
    target function void    write_bytes(addr_handle_t hndl, list<bit[8]> data,
                                       mem_access_desc_s mem_access_desc = {});
    target function void    read_struct/write_struct(addr_handle_t hndl,
                                       struct packed_struct,
                                       mem_access_desc_s mem_access_desc = {});

``mem_access_desc_s`` is empty in the standard; extend it to carry access
attributes:

.. code-block:: pss

    extend struct mem_access_desc_s { int priority; }

The same access API — everything above **except** ``read_struct`` and
``write_struct`` — is also extended onto ``executor_base_c``, so that an
access may be directed at a specific executor rather than the default one:

.. code-block:: pss

    comp.my_executor.write32(hndl, 32'hdead_beef);

Register model (21.14)
~~~~~~~~~~~~~~~~~~~~~~

A three-level hierarchy. Each level exists so that a model can be written
against the loosest one that will do:

.. code-block:: text

    reg_base_c              -- a register with an address and nothing else
      └─ reg_sized_c<SZ>    -- a register of a known width, field layout unknown
           └─ reg_c<R,ACC,SZ>  -- a register with a value type R

.. code-block:: pss

    pure component reg_base_c {
        function addr_handle_t get_handle();
    }

    pure component reg_sized_c<int SZ> : reg_base_c {
        target function bit[SZ] read_val();
        target function void    write_val(bit[SZ] r);
        target function void    write_val_masked(bit[SZ] mask, bit[SZ] val);
        target function void    write_field(string name, bit[SZ] val);
        target function void    write_fields(list<string> names, list<bit[SZ]> vals);
    }

    enum reg_access {READWRITE, READONLY, WRITEONLY};

    pure component reg_c<type R, reg_access ACC = READWRITE,
                         int SZ = (8*sizeof_s<R>::nbytes)> : reg_sized_c<SZ> {
        target function R    read();
        target function void write(R r);
        target function void write_masked(R mask, R val);
    };

``reg_sized_c<SZ>`` is what makes generic access across same-width registers
possible regardless of field layout — ``read_val``/``write_val`` deal in
``bit[SZ]``, while ``reg_c``'s ``read``/``write`` deal in the register's value
type ``R``.

Register groups:

.. code-block:: pss

    struct node_s { string name; int index; };

    pure component reg_group_c {
        pure  function bit[64] get_offset_of_instance(string name);
        pure  function bit[64] get_offset_of_instance_array(string name, int index);
        pure  function bit[64] get_offset_of_path(list<node_s> path);
        solve function void    set_handle(addr_handle_t addr);
        function addr_handle_t get_handle();

        solve pure function string get_mnemonic_of_instance(string name);
        solve pure function string get_mnemonic_of_instance_array(string name, int index);
        solve pure function string get_mnemonic_of_path(list<node_s> path);
        solve function void        set_mnemonic(string prefix);
    };

    solve function void use_symbolic_reg_names(ref reg_group_c grp, bool enable);

``sync_pkg``
------------

.. code-block:: pss

    component channel_c<type T, int DEPTH=1> {
        target function T    get();
        target function void put(T t);
        target function bool try_get(output T t);
        target function bool try_put(T t);
    }

All four are ``target`` functions: callable from ``body``, ``run_start``,
``run_end`` and functions reached from them, never from a solve exec.

.. _stdlib-qualifiers:

What is *not* enforced
----------------------

The declarations above carry the ``solve``, ``target`` and ``pure``
qualifiers Annex C gives them, but **platform availability is not checked**.
A ``solve`` function called from a target ``exec`` is accepted, and a
``target`` function called from a solve ``exec`` likewise. Writing
``print(...)`` in an ``exec body`` is non-conforming PSS and will be rejected
when the check lands. Tracked as ``CL-S4`` in
``docs/design/known-issues.md``.

``pure`` *is* checked, in the contexts where the LRM requires it — see
``PSS114`` in :doc:`checker_plugin_guide`.

Departures from Annex C
-----------------------

pssparser's core library is Annex C plus exactly one extra, and it is
deliberate:

.. list-table::
   :header-rows: 1

   * - Declaration
     - Status
   * - ``std_pkg::format_string(string format, type... args)``
     - **Non-standard.** Not a member of ``std_pkg`` in the standard; it
       appears only in Example 294, as an illustration of varargs. Retained
       for compatibility with existing models. Do not use it in portable PSS —
       ``format`` is the standard spelling.

Three other non-standard entries were removed in the 3.1 alignment —
``std_pkg::actor_c``, ``executor_pkg::executor_group_default_c``, and
``channel_c``'s ``put_a``/``get_a`` actions. See :doc:`pss31_migration` for
what to use instead.

See Also
========

* :doc:`pss31_migration` — what changed, and what it breaks.
* :doc:`pss31_features` — the PSS 3.1 language features.
* ``docs/design/core-library-conformance-plan.md`` — the Annex C alignment
  work, and what remains.
