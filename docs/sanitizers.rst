Building with sanitizers
========================

.. code-block:: sh

   cmake .. -DENABLE_ASAN=ON      # AddressSanitizer
   cmake .. -DENABLE_UBSAN=ON     # UndefinedBehaviorSanitizer

Both add the compile *and* link flags, and both are forwarded to every
``ExternalProject`` -- the ANTLR runtime, the generated AST library, and gtest
-- so the whole program is instrumented rather than just the sources in this
repository. See ``FORWARDED_BUILD_ARGS`` in the top-level ``CMakeLists.txt``.

Running the Python suite against an instrumented build
------------------------------------------------------

The build is only half of it. ``pssparser.core`` does not link
``libpssparser.so``; it ``dlopen``\ s it (``python/core.pyx``), and the ASan
runtime has to be loaded before anything it interposes on.

.. code-block:: sh

   export LD_PRELOAD="$(gcc -print-file-name=libasan.so):$(gcc -print-file-name=libstdc++.so)"
   export ASAN_OPTIONS=detect_leaks=0:halt_on_error=0:print_stacktrace=1:log_path=/tmp/asan
   python -m pytest tests/python -q

Three things that are not obvious:

**libstdc++ must be preloaded alongside the runtime.** ``python`` is not linked
against it, so at ASan init ``__cxa_throw`` is unresolvable and the first C++
exception aborts the process with::

   AddressSanitizer: CHECK failed: asan_interceptors.cpp:458
   "((__interception::real___cxa_throw)) != (0)"

ANTLR throws one per error-recovery ``sync()``, so this fires within seconds.
It is a tooling artifact, not a finding.

**detect_leaks=0.** CPython leaks by design at interpreter teardown, and once
the runtime is preloaded every allocation is intercepted, so LSan output buries
anything real.

**The library the extension finds is the one it dlopens**, which is
``<package>/../../build/{lib,lib64,bin,src}/``. Building into the default
``build/`` therefore replaces what a normal run uses. To keep an instrumented
build alongside a stock one, put it elsewhere and point a scratch root at it:

.. code-block:: sh

   cmake /path/to/pssparser -GNinja -DENABLE_ASAN=ON \
       -DPACKAGES_DIR=/path/to/packages -DCMAKE_INSTALL_PREFIX=$ROOT/build
   ninja && ninja install          # install is required: libast.so only reaches
                                   # build/lib on install
   ln -s /path/to/pssparser/python $ROOT/python
   ln -s /path/to/pssparser/src    $ROOT/src
   PYTHONPATH=$ROOT/python python -m pytest ...

``core.pyx`` uses ``os.path.abspath`` rather than ``realpath``, which is what
makes the symlinked root work. The ``src`` link is needed because
``get_stdlib_dir()`` falls back to ``<pkg>/../../src/stdlib`` in a source
checkout; without it three ``test_doc_comments.py`` tests fail for reasons that
have nothing to do with the sanitizer.

Confirm what actually loaded before trusting a clean run:

.. code-block:: sh

   python -c "import pssparser.core as c; c.Factory.inst()
   print([l.split()[-1] for l in open('/proc/self/maps')
          if 'libpssparser' in l or 'libasan' in l][:2])"
