#****************************************************************************
#* CMakeLists.txt -- pssparser WebAssembly build
#*
#* A separate configuration, not a variant of the native one
#* (ts-wasm-impl-plan.md §1.5). The native build is a chain of
#* ExternalProjects with install rules, RPATH handling and MSVC workarounds,
#* none of which apply here: under Emscripten there are no shared libraries to
#* find at runtime, nothing to install, and one link step produces the whole
#* deliverable.
#*
#* Drive it through emcmake so the Emscripten toolchain file is selected:
#*
#*   source scripts/wasm-env.sh
#*   emcmake cmake -S wasm -B build-wasm -DCMAKE_BUILD_TYPE=Release
#*   cmake --build build-wasm -j
#*
#* Output lands in ts/src/wasm/pssparser.{js,wasm}.
#****************************************************************************
cmake_minimum_required(VERSION 3.16)
project(pssparser_wasm CXX)

if (NOT EMSCRIPTEN)
  message(FATAL_ERROR
    "wasm/CMakeLists.txt must be configured through emcmake. "
    "Run `source scripts/wasm-env.sh` then `emcmake cmake -S wasm -B build-wasm`.")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

#****************************************************************************
#* ENABLE_ASAN -- a diagnostic build, never the shipped one
#*
#*   emcmake cmake -S wasm -B build-wasm-asan -DENABLE_ASAN=ON
#*   cmake --build build-wasm-asan -j
#*   node wasm/asan-probe.mjs build-wasm-asan
#*
#* This exists for one class of bug that the test suite provably cannot see.
#* AstBuilderInt::build keeps borrowed pointers to every unit it has processed
#* (AstBuilderInt.cpp:153), so a unit freed after a failed parse leaves a
#* dangling pointer for the next parse to read. bindings.cpp handles that by
#* retiring failed units -- and with the fix reverted, the whole suite still
#* passes, because the freed block is not recycled and the read returns
#* stale-but-intact data. Nothing observable differs.
#*
#* ASan is what makes the difference observable. The native build has had
#* -DENABLE_ASAN=ON for a long time; the WASM build did not, which is why the
#* fix shipped in Phase 1 justified only by reading the code.
#*
#* Not a variant of the release build: ASan replaces the allocator and roughly
#* triples the artifact, so it is a separate build directory used deliberately.
#****************************************************************************
option(ENABLE_ASAN "Build with AddressSanitizer (diagnostic only, not shippable)" OFF)

get_filename_component(PSSPARSER_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(PACKAGES_DIR "${PSSPARSER_ROOT}/packages")
set(ANTLR_JAR "${PACKAGES_DIR}/antlr4-tools.jar")
set(ANTLR_RUNTIME "${PACKAGES_DIR}/antlr4-cpp-runtime/runtime/src")

#****************************************************************************
#* PYTHON -- searched upward, not assumed to be ours
#*
#* Under `deps-mode: nested` a consumer places pssparser's own directory
#* dependencies in <pssparser>/packages/, which is why ANTLR_JAR above is
#* still right. The Python venv is the exception: ivpm's python handler is
#* root-scoped, so the venv belongs to the *consuming* workspace and there is
#* no <pssparser>/packages/python at all.
#*
#* So walk up the enclosing deps-dirs looking for one. A standalone checkout
#* finds its own on the first try and nothing changes; a nested one finds the
#* consumer's, which is the venv astbuilder was actually installed into.
#* -DPSSPARSER_PYTHON=... overrides for anyone whose layout is neither.
#****************************************************************************
if (NOT PSSPARSER_PYTHON)
  set(_py_search "${PSSPARSER_ROOT}")
  foreach (_i RANGE 6)
    if (EXISTS "${_py_search}/packages/python/bin/python")
      set(PSSPARSER_PYTHON "${_py_search}/packages/python/bin/python")
      break()
    endif()
    get_filename_component(_py_parent "${_py_search}" DIRECTORY)
    if (_py_parent STREQUAL _py_search)
      break()
    endif()
    set(_py_search "${_py_parent}")
  endforeach()
endif()
set(PYTHON "${PSSPARSER_PYTHON}")

if (NOT PYTHON OR NOT EXISTS "${PYTHON}")
  message(FATAL_ERROR
    "no IVPM Python environment found at or above ${PSSPARSER_ROOT} -- "
    "run `ivpm update -d ts-build`, or pass -DPSSPARSER_PYTHON=<python>")
endif()
message(STATUS "pssparser-wasm: python: ${PYTHON}")

#****************************************************************************
#* DMGR_INCLUDE -- debug-mgr's C++ headers, which ship inside the wheel
#*
#* debug-mgr is a PyPI dependency that carries headers, so the include path is
#* a site-packages path. Derived from PYTHON rather than written out, for two
#* reasons this used to get wrong: the venv is not necessarily under our own
#* packages/ (see above), and the interpreter version is not necessarily 3.12
#* -- the path was hardcoded to `python3.12`, which is a dependency on the
#* machine that happened to build it first.
#****************************************************************************
get_filename_component(_venv_bin "${PYTHON}" DIRECTORY)
get_filename_component(PSSPARSER_VENV "${_venv_bin}" DIRECTORY)

file(GLOB DMGR_INCLUDE
  "${PSSPARSER_VENV}/lib/python*/site-packages/debug_mgr/share/include"
  "${PSSPARSER_VENV}/Lib/site-packages/debug_mgr/share/include")

if (NOT DMGR_INCLUDE)
  message(FATAL_ERROR
    "debug-mgr headers not found under ${PSSPARSER_VENV} -- the wasm build "
    "compiles against them. Run `ivpm update -d ts-build`.")
endif()
message(STATUS "pssparser-wasm: dmgr headers: ${DMGR_INCLUDE}")

foreach (req "${ANTLR_JAR}" "${ANTLR_RUNTIME}")
  if (NOT EXISTS "${req}")
    message(FATAL_ERROR "missing dependency: ${req} -- run `ivpm update -d ts-build`")
  endif()
endforeach()

find_package(Java COMPONENTS Runtime REQUIRED)

#****************************************************************************
#* Generated sources
#*
#* All three generators run at configure time rather than as build rules.
#* Under Emscripten every one of them is a host-tool invocation that produces
#* a fixed file set from a fixed input set, and running them here means the
#* glob below sees the result -- a build-time custom command would need the
#* file list up front, which is exactly what the generator decides.
#*
#* CMAKE_CONFIGURE_DEPENDS carries the invalidation: editing ast/*.yaml or a
#* .g4 re-runs configure, which re-runs the generator. The native build learned
#* this the hard way (CMakeLists.txt:243-251) -- an ExternalProject
#* DOWNLOAD_COMMAND that is really a code generator is stamped once and never
#* re-stamped, so a schema edit surfaced as a missing accessor on the generated
#* class rather than as a stale build.
#****************************************************************************
file(GLOB AST_SPEC "${PSSPARSER_ROOT}/ast/*.yaml")
file(GLOB STDLIB_SPEC "${PSSPARSER_ROOT}/src/stdlib/*.pss")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  ${AST_SPEC}
  ${STDLIB_SPEC}
  "${PSSPARSER_ROOT}/src/PSSLexer.g4"
  "${PSSPARSER_ROOT}/src/PSSParser.g4")

set(GEN_DIR "${CMAKE_BINARY_DIR}/generated")
set(AST_GEN_DIR "${GEN_DIR}/ast")
set(ANTLR_GEN_DIR "${GEN_DIR}/antlr")
file(MAKE_DIRECTORY "${AST_GEN_DIR}" "${ANTLR_GEN_DIR}")

# -- AST data structures -----------------------------------------------------
# Same generator and same arguments as scripts/gen_ast.py, so the WASM core and
# the native core are compiled against byte-identical headers. gen-cpp writes
# relative to the working directory, hence WORKING_DIRECTORY rather than -o.
message(STATUS "pssparser-wasm: generating AST into ${AST_GEN_DIR}")
execute_process(
  COMMAND "${PYTHON}" -m astbuilder gen-cpp
          -name ast -namespace pssp::ast
          -astdir "${PSSPARSER_ROOT}/ast"
          -license "${PSSPARSER_ROOT}/etc/copyright.cpp"
  WORKING_DIRECTORY "${AST_GEN_DIR}"
  RESULT_VARIABLE _ast_rc
  OUTPUT_VARIABLE _ast_out
  ERROR_VARIABLE _ast_out)
if (NOT _ast_rc EQUAL 0)
  message(FATAL_ERROR "astbuilder gen-cpp failed (${_ast_rc}):\n${_ast_out}")
endif()

# -- ANTLR lexer/parser ------------------------------------------------------
# Generated into a staging directory and then copied in with
# copy_if_different, rather than written straight to ANTLR_GEN_DIR.
#
# Everything else on this page is generated by something we control, and those
# generators were taught to compare before writing. ANTLR is a third-party jar
# that rewrites its whole output unconditionally -- and since this runs at
# cmake *configure* time, and an explicit `cmake -S -B` always re-configures,
# an unconditional rewrite made PSSParser.cpp (the single largest object in the
# build) newer than its .o on every invocation. Staging moves the comparison
# outside the tool.
set(ANTLR_STAGE_DIR "${GEN_DIR}/antlr-stage")
message(STATUS "pssparser-wasm: generating ANTLR front end")
execute_process(
  COMMAND "${Java_JAVA_EXECUTABLE}" -jar "${ANTLR_JAR}"
          -Dlanguage=Cpp -listener -visitor
          -o "${ANTLR_STAGE_DIR}"
          "${PSSPARSER_ROOT}/src/PSSLexer.g4" "${PSSPARSER_ROOT}/src/PSSParser.g4"
  RESULT_VARIABLE _antlr_rc
  OUTPUT_VARIABLE _antlr_out
  ERROR_VARIABLE _antlr_out)
if (NOT _antlr_rc EQUAL 0)
  message(FATAL_ERROR "antlr4 failed (${_antlr_rc}):\n${_antlr_out}")
endif()
# antlr mirrors the input path under -o; the .g4 files live in src/.
set(ANTLR_STAGE_OUT_DIR "${ANTLR_STAGE_DIR}")
if (EXISTS "${ANTLR_STAGE_DIR}/src")
  set(ANTLR_STAGE_OUT_DIR "${ANTLR_STAGE_DIR}/src")
endif()

# Flattened on the way in, so ANTLR_OUT_DIR no longer depends on where antlr
# chose to mirror the input path.
set(ANTLR_OUT_DIR "${ANTLR_GEN_DIR}")
file(GLOB _antlr_staged "${ANTLR_STAGE_OUT_DIR}/*")
foreach(_f IN LISTS _antlr_staged)
  get_filename_component(_fname "${_f}" NAME)
  execute_process(COMMAND "${CMAKE_COMMAND}" -E copy_if_different
                          "${_f}" "${ANTLR_OUT_DIR}/${_fname}")
endforeach()

# -- Embedded standard library ----------------------------------------------
# The stdlib is compiled into the binary as bytes, which is what lets the WASM
# build run with -sFILESYSTEM=0 (ts-api-design.md §3.1). This is not a
# concession made for WASM: the native build already does it.
execute_process(
  COMMAND "${PYTHON}" "${PSSPARSER_ROOT}/src/stdlib/mk_pssstdlib.py"
          "${GEN_DIR}/pss_stdlib.h"
  RESULT_VARIABLE _stdlib_rc
  OUTPUT_VARIABLE _stdlib_out
  ERROR_VARIABLE _stdlib_out)
if (NOT _stdlib_rc EQUAL 0)
  message(FATAL_ERROR "mk_pssstdlib.py failed (${_stdlib_rc}):\n${_stdlib_out}")
endif()

# -- AST serialisation pair --------------------------------------------------
# The C++ writer and the TypeScript reader of the AST wire format, emitted
# together from one schema in one run (gen_wasm.py explains why that matters).
#
# This step -- not `npm run gen:ast` -- is the sole producer of deserialize.ts,
# for the same reason the schema hash below has a single producer: the file has
# to agree with a .cpp that only this build compiles. gen-ts owns classes.ts and
# the rest of that directory and does not touch this file, so the two generators
# share the tree without sharing an output.
set(SERIALIZER_DIR "${GEN_DIR}/serializer")
message(STATUS "pssparser-wasm: generating AST serialisation pair")
execute_process(
  COMMAND "${PYTHON}" -m astbuilder gen-wasm
          -astdir "${PSSPARSER_ROOT}/ast"
          -cpp "${SERIALIZER_DIR}"
          -ts "${PSSPARSER_ROOT}/ts/src/ast/generated"
          -license "${PSSPARSER_ROOT}/etc/copyright.cpp"
  RESULT_VARIABLE _ser_rc
  OUTPUT_VARIABLE _ser_out
  ERROR_VARIABLE _ser_out)
if (NOT _ser_rc EQUAL 0)
  message(FATAL_ERROR "astbuilder gen-wasm failed (${_ser_rc}):\n${_ser_out}")
endif()

# -- Schema hash -------------------------------------------------------------
# Emitted for both sides at once, from the same inputs, in the same run. The
# C++ half is compiled into the .wasm and the TS half into the package; the
# loader compares them (ts-api-design.md §7). Generating them together is the
# point -- two generators could disagree, which is the failure this check
# exists to catch.
execute_process(
  COMMAND "${PYTHON}" "${PSSPARSER_ROOT}/scripts/gen_schema_hash.py"
          "${PSSPARSER_ROOT}/ast"
          -H "${GEN_DIR}/pssparser_schema_hash.h"
          -T "${PSSPARSER_ROOT}/ts/src/wasm/schemaHash.ts"
  RESULT_VARIABLE _hash_rc
  OUTPUT_VARIABLE _hash_out
  ERROR_VARIABLE _hash_out)
if (NOT _hash_rc EQUAL 0)
  message(FATAL_ERROR "gen_schema_hash.py failed (${_hash_rc}):\n${_hash_out}")
endif()
string(STRIP "${_hash_out}" _hash_out)
message(STATUS "pssparser-wasm: ${_hash_out}")

#****************************************************************************
#* Sources
#****************************************************************************
file(GLOB_RECURSE ANTLR_RUNTIME_SRC "${ANTLR_RUNTIME}/*.cpp")
file(GLOB AST_SRC "${AST_GEN_DIR}/*.cpp")
file(GLOB PSSPARSER_SRC "${PSSPARSER_ROOT}/src/*.cpp")
file(GLOB ANTLR_FRONTEND_SRC "${ANTLR_OUT_DIR}/*.cpp")

list(LENGTH AST_SRC _n_ast)
list(LENGTH ANTLR_FRONTEND_SRC _n_fe)
if (_n_ast EQUAL 0 OR _n_fe EQUAL 0)
  message(FATAL_ERROR
    "generation produced nothing: ${_n_ast} AST sources, ${_n_fe} front-end sources")
endif()

add_executable(pssparser
  ${ANTLR_RUNTIME_SRC}
  ${ANTLR_FRONTEND_SRC}
  ${AST_SRC}
  ${PSSPARSER_SRC}
  "${SERIALIZER_DIR}/AstSerializer.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/bindings.cpp")

target_include_directories(pssparser PRIVATE
  "${ANTLR_RUNTIME}"
  "${ANTLR_OUT_DIR}"
  "${AST_GEN_DIR}/include"
  "${SERIALIZER_DIR}"
  "${GEN_DIR}"
  "${PSSPARSER_ROOT}/src"
  "${PSSPARSER_ROOT}/src/include"
  ${DMGR_INCLUDE})

# ANTLR4CPP_STATIC turns off the dllimport/dllexport decorations. There is no
# dynamic linking under Emscripten, so the decorated form is meaningless here.
target_compile_definitions(pssparser PRIVATE ANTLR4CPP_STATIC)
target_compile_options(pssparser PRIVATE
  -Wno-attributes
  # The generated parser's serialized ATN is a very large initializer and the
  # AST headers instantiate deep template chains; neither is a diagnostic worth
  # reading 20k times.
  -Wno-unused-command-line-argument)

#****************************************************************************
#* Link
#*
#* -sFILESYSTEM=0 is the load-bearing flag: it is viable only because the
#* TypeScript API has no parse(paths) (ts-api-design.md §3.1), and it is what
#* keeps the module usable unchanged in a browser.
#*
#* No pthreads. ANTLR's synchronization primitives (internal/Synchronization.h)
#* are std::mutex/std::shared_mutex wrappers, and Emscripten's libc++ provides
#* single-threaded no-op implementations of those, so the runtime compiles and
#* runs correctly without a threading build. Enabling pthreads would cost a
#* SharedArrayBuffer requirement and the cross-origin isolation headers that go
#* with it, for a parser that is single-threaded anyway.
#****************************************************************************
set(PSSPARSER_LINK_FLAGS
  "-lembind"
  "-sMODULARIZE=1"
  "-sEXPORT_ES6=1"
  "-sEXPORT_NAME=createPssParserModule"
  "-sALLOW_MEMORY_GROWTH=1"
  "-sFILESYSTEM=0"
  "-sENVIRONMENT=web,worker,node"
  # Embind marshals std::string by value across the boundary; without this the
  # module refuses to accept a JS string longer than the initial heap.
  "-sDYNAMIC_EXECUTION=0"
  # A C++ exception escaping into JS is a binding bug, but it must surface as
  # an Error with the what() text rather than as an unreachable trap
  # (ts-api-design.md §3.3).
  "-fexceptions"
  "-sDISABLE_EXCEPTION_CATCHING=0")

target_compile_options(pssparser PRIVATE -fexceptions)

if (ENABLE_ASAN)
  # ALLOW_MEMORY_GROWTH is dropped rather than kept: Emscripten's ASan reserves
  # its shadow memory against the initial heap, and a growing heap invalidates
  # it. INITIAL_MEMORY replaces it with a fixed, large heap -- workable for a
  # diagnostic run over one file, which is all this build is for.
  list(REMOVE_ITEM PSSPARSER_LINK_FLAGS "-sALLOW_MEMORY_GROWTH=1")
  list(APPEND PSSPARSER_LINK_FLAGS
    "-fsanitize=address"
    "-sINITIAL_MEMORY=1073741824"
    "-sSTACK_SIZE=4194304"
    # -g2, not -gsource-map. The source-map variant emits an addRunDependency
    # call outside the MODULARIZE closure, so the ES6 module throws
    # `addRunDependency is not defined` before it ever instantiates. Function
    # names in the ASan report survive at -g2; the line numbers do not, which is
    # a fair trade for a module that loads.
    "-g2")
  target_compile_options(pssparser PRIVATE -fsanitize=address -g)
  message(STATUS "pssparser-wasm: AddressSanitizer ENABLED -- diagnostic build")
endif()

target_link_options(pssparser PRIVATE ${PSSPARSER_LINK_FLAGS})

# The release build writes straight into the TypeScript package; the ASan build
# must not, or a diagnostic artifact three times the size and with a different
# allocator becomes the one that ships. It stays in its own build directory,
# which is where wasm/asan-probe.mjs looks for it.
set(PSSPARSER_OUT_DIR "${PSSPARSER_ROOT}/ts/src/wasm")
if (ENABLE_ASAN)
  set(PSSPARSER_OUT_DIR "${CMAKE_BINARY_DIR}")
endif()

set_target_properties(pssparser PROPERTIES
  OUTPUT_NAME pssparser
  SUFFIX ".js"
  RUNTIME_OUTPUT_DIRECTORY "${PSSPARSER_OUT_DIR}")
