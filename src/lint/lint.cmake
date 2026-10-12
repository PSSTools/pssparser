#****************************************************************************
#* lint.cmake -- sources and dependencies of the lint engine (src/lint/)
#*
#* Included by both src/CMakeLists.txt (native) and wasm/CMakeLists.txt, so
#* the two builds compile the same file set from the same place
#* (lint-core-plan.md C1.1: a source missing from one build gives a
#* native/WASM split that only the parity tests would catch).
#*
#* Inputs:  PACKAGES_DIR, PSSPARSER_LINT_DIR (this directory), PYTHON
#* Outputs: PSSPARSER_LINT_SRC      lint engine + rapidyaml + c4core sources,
#*                                  and the generated reflection tables
#*          PSSPARSER_LINT_INCLUDE  include directories they need
#*
#* rapidyaml comes from ivpm (D-C2, D-C5), as the v0.16.0 source release.
#* ivpm keeps the archive's top directory, so the tree is
#* ${PACKAGES_DIR}/rapidyaml/rapidyaml.v<ver>/{src,ext/c4core.src}. The
#* versioned directory is found by glob rather than written out, so a version
#* bump is an ivpm.yaml change only.
#****************************************************************************

file(GLOB _ryml_hpp "${PACKAGES_DIR}/rapidyaml/*/src/ryml.hpp")
list(LENGTH _ryml_hpp _ryml_n)
if (NOT _ryml_n EQUAL 1)
  message(FATAL_ERROR
    "lint: expected one rapidyaml source tree under ${PACKAGES_DIR}/rapidyaml, "
    "found ${_ryml_n} -- run `ivpm update`")
endif()
get_filename_component(_ryml_src_dir "${_ryml_hpp}" DIRECTORY)
get_filename_component(RAPIDYAML_ROOT "${_ryml_src_dir}" DIRECTORY)

# The same file list rapidyaml's own build uses for its bundled c4core
# (ext/c4core.src.txt), less the headers.
file(GLOB_RECURSE _ryml_src "${RAPIDYAML_ROOT}/src/c4/yml/*.cpp")
file(GLOB _c4core_src "${RAPIDYAML_ROOT}/ext/c4core.src/c4/*.cpp")

# CONFIGURE_DEPENDS: a new engine source is picked up by the next build, not
# only by the next explicit configure (the WASM build otherwise links without
# it and fails on undefined symbols).
file(GLOB_RECURSE _lint_src CONFIGURE_DEPENDS "${PSSPARSER_LINT_DIR}/*.cpp")

set(PSSPARSER_LINT_SRC ${_lint_src} ${_ryml_src} ${_c4core_src})
set(PSSPARSER_LINT_INCLUDE
  "${RAPIDYAML_ROOT}/src"
  "${RAPIDYAML_ROOT}/ext/c4core.src")

#****************************************************************************
#* Reflection tables (lint-core-plan.md C1.3, D-C3): field access by name for
#* the CEL engine, generated from ast/*.yaml by pyastbuilder's gen-reflect,
#* the same schema every other AST product comes from. A build-time rule: the
#* outputs are known in advance, and the rule re-runs when the schema or the
#* generator changes.
#****************************************************************************
get_filename_component(_lint_root "${PSSPARSER_LINT_DIR}/../.." ABSOLUTE)
set(PSSPARSER_REFLECT_DIR "${CMAKE_CURRENT_BINARY_DIR}/lint-reflect")
file(GLOB _lint_ast_spec CONFIGURE_DEPENDS "${_lint_root}/ast/*.yaml")
set(_lint_reflect_deps ${_lint_ast_spec})
# The generator's own source, when pyastbuilder is a source checkout
# (default-dev); a PyPI install has no stable path to depend on.
if (EXISTS "${PACKAGES_DIR}/pyastbuilder/src/astbuilder/gen_reflect.py")
  list(APPEND _lint_reflect_deps "${PACKAGES_DIR}/pyastbuilder/src/astbuilder/gen_reflect.py")
endif()
add_custom_command(
  OUTPUT "${PSSPARSER_REFLECT_DIR}/Reflect.h" "${PSSPARSER_REFLECT_DIR}/Reflect.cpp"
  COMMAND "${PYTHON}" -m astbuilder gen-reflect
          -astdir "${_lint_root}/ast"
          -o "${PSSPARSER_REFLECT_DIR}"
          -namespace pssp::ast
          -license "${_lint_root}/etc/copyright.cpp"
  DEPENDS ${_lint_reflect_deps}
  COMMENT "Generating the lint engine's AST reflection tables"
  VERBATIM)

list(APPEND PSSPARSER_LINT_SRC "${PSSPARSER_REFLECT_DIR}/Reflect.cpp")
list(APPEND PSSPARSER_LINT_INCLUDE "${PSSPARSER_REFLECT_DIR}")

#****************************************************************************
#* Built-in rule files (lint-core-plan.md C4.3; pss-rules-format.md §6.2):
#* rules/*.yaml at the repository root, embedded as bytes, as the standard
#* library is. The generator is a dependency too, so editing it re-runs the
#* rule (see the stdlib rule in src/CMakeLists.txt for why that matters).
#****************************************************************************
set(PSSPARSER_BUILTIN_RULES_DIR "${CMAKE_CURRENT_BINARY_DIR}/lint-builtin")
file(GLOB _lint_builtin_rules CONFIGURE_DEPENDS
  "${_lint_root}/rules/*.yaml" "${_lint_root}/rules/*.yml")
add_custom_command(
  OUTPUT "${PSSPARSER_BUILTIN_RULES_DIR}/BuiltinRules.cpp"
  COMMAND "${PYTHON}" "${PSSPARSER_LINT_DIR}/rules/mk_builtin_rules.py"
          "${_lint_root}/rules"
          "${PSSPARSER_BUILTIN_RULES_DIR}/BuiltinRules.cpp"
  DEPENDS ${_lint_builtin_rules} "${PSSPARSER_LINT_DIR}/rules/mk_builtin_rules.py"
  COMMENT "Embedding the built-in lint rule files"
  VERBATIM)

list(APPEND PSSPARSER_LINT_SRC "${PSSPARSER_BUILTIN_RULES_DIR}/BuiltinRules.cpp")
# The generated file includes "rules/BuiltinRules.h", from beside this file.
set_source_files_properties("${PSSPARSER_BUILTIN_RULES_DIR}/BuiltinRules.cpp"
  PROPERTIES INCLUDE_DIRECTORIES "${PSSPARSER_LINT_DIR}")

#****************************************************************************
#* The marker catalogue (lint-core-plan.md C7.3): catalog/catalog.json, which
#* scripts/gen_catalog.py generates from the Python MarkerDefs and which is
#* checked in, embedded as bytes as the built-in rules are.
#****************************************************************************
set(PSSPARSER_CATALOG_DIR "${CMAKE_CURRENT_BINARY_DIR}/lint-catalog")
add_custom_command(
  OUTPUT "${PSSPARSER_CATALOG_DIR}/CatalogData.cpp"
  COMMAND "${PYTHON}" "${PSSPARSER_LINT_DIR}/catalog/mk_catalog.py"
          "${PSSPARSER_LINT_DIR}/catalog/catalog.json"
          "${PSSPARSER_CATALOG_DIR}/CatalogData.cpp"
  DEPENDS "${PSSPARSER_LINT_DIR}/catalog/catalog.json"
          "${PSSPARSER_LINT_DIR}/catalog/mk_catalog.py"
  COMMENT "Embedding the marker catalogue"
  VERBATIM)

list(APPEND PSSPARSER_LINT_SRC "${PSSPARSER_CATALOG_DIR}/CatalogData.cpp")
set_source_files_properties("${PSSPARSER_CATALOG_DIR}/CatalogData.cpp"
  PROPERTIES INCLUDE_DIRECTORIES "${PSSPARSER_LINT_DIR}")
