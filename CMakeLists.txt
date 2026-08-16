cmake_minimum_required (VERSION 3.11)

project(pssparser)

include(ExternalProject)

set(CMAKE_INSTALL_RPATH $ORIGIN)

if (NOT PACKAGES_DIR)
  set(PACKAGES_DIR ${CMAKE_SOURCE_DIR}/packages)

  set(ENABLE_TESTS True)

endif()

if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  message("Set CMAKE_INSTALL_PREFIX")
  set (CMAKE_INSTALL_PREFIX ${CMAKE_BINARY_DIR})
else()
  message("CMAKE_INSTALL_PREFIX set to ${CMAKE_INSTALL_PREFIX}")
endif()

# Force DLLs (RUNTIME artifacts) to install into lib/ so ivpm can find them
set(CMAKE_INSTALL_BINDIR "lib" CACHE PATH "Installation directory for executables" FORCE)

message("PSSParser: PACKAGES_DIR=${PACKAGES_DIR}")


list(APPEND CMAKE_MODULE_PATH ${PACKAGES_DIR}/antlr4-cpp-runtime/cmake)

# Generated AST headers
include_directories(${CMAKE_BINARY_DIR}/pssparser_ast/src/include)

link_directories(
	${CMAKE_BINARY_DIR}/antlr4/lib
	${CMAKE_BINARY_DIR}/pssparser_ast/lib
	)

set(ANTLR_EXECUTABLE ${PACKAGES_DIR}/antlr4-tools.jar)
set(ANTLR4_JAR_LOCATION ${PACKAGES_DIR}/antlr4-tools.jar)

if (WIN32)
  set(PYTHON ${PACKAGES_DIR}/python/Scripts/python.exe)
else()
  set(PYTHON ${PACKAGES_DIR}/python/bin/python)
endif()

find_package(ANTLR REQUIRED)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS True)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  set(ANTLR_CXXFLAGS "-Wno-attributes -fPIC")
elseif (MSVC)
  # antlr4-cpp-runtime 4.13.2 omits <chrono> include and lacks /EHsc with MSVC
  set(ANTLR_CXXFLAGS "/EHsc /FIchrono -DANTLR4CPP_STATIC")
else()
  set(ANTLR_CXXFLAGS "-DANTLR4CPP_STATIC")
endif()

set(CompilerFlags
        CMAKE_CXX_FLAGS
        CMAKE_CXX_FLAGS_DEBUG
        CMAKE_CXX_FLAGS_RELEASE
        CMAKE_C_FLAGS
        CMAKE_C_FLAGS_DEBUG
        CMAKE_C_FLAGS_RELEASE
        "-fPIC"
        )
foreach(CompilerFlag ${CompilerFlags})
  string(REPLACE "/MD" "/MT" ${CompilerFlag} "${${CompilerFlag}}")
  string(REPLACE "/MDd" "/MTd" ${CompilerFlag} "${${CompilerFlag}}")
endforeach()

#********************************************************************
#* Sanitizers
#*
#*   cmake .. -DENABLE_ASAN=ON
#*
#* Applied to CMAKE_{C,CXX}_FLAGS *before* the forwarding block below, so it
#* reaches the dependencies too. See docs/sanitizers.rst for running the suite
#* against the result -- the build is only half of it, because the extension
#* modules dlopen libpssparser.so and the ASan runtime has to be preloaded.
#*
#* `-fno-omit-frame-pointer` is not optional in practice: without it the stack
#* in a report stops at the first frame the optimizer flattened, which on a
#* recursive-descent parser is most of them.
#********************************************************************
option(ENABLE_ASAN "Build with AddressSanitizer" OFF)
option(ENABLE_UBSAN "Build with UndefinedBehaviorSanitizer" OFF)

set(SANITIZER_FLAGS "")
if (ENABLE_ASAN)
  string(APPEND SANITIZER_FLAGS " -fsanitize=address -fno-omit-frame-pointer -g")
endif()
if (ENABLE_UBSAN)
  string(APPEND SANITIZER_FLAGS " -fsanitize=undefined -fno-omit-frame-pointer -g")
endif()

if (NOT SANITIZER_FLAGS STREQUAL "")
  if (MSVC AND ENABLE_UBSAN)
    message(FATAL_ERROR "ENABLE_UBSAN: MSVC has no UndefinedBehaviorSanitizer")
  endif()
  string(APPEND CMAKE_C_FLAGS "${SANITIZER_FLAGS}")
  string(APPEND CMAKE_CXX_FLAGS "${SANITIZER_FLAGS}")
  # A sanitizer is a link-time decision as well as a compile-time one: the
  # runtime is a library, and an instrumented object linked without it fails
  # on undefined __asan_* symbols.
  string(APPEND CMAKE_EXE_LINKER_FLAGS "${SANITIZER_FLAGS}")
  string(APPEND CMAKE_SHARED_LINKER_FLAGS "${SANITIZER_FLAGS}")
  string(APPEND CMAKE_MODULE_LINKER_FLAGS "${SANITIZER_FLAGS}")
  message(STATUS "Sanitizers enabled:${SANITIZER_FLAGS}")
endif()

#********************************************************************
#* Build settings forwarded to every ExternalProject
#*
#* An ExternalProject is a SEPARATE cmake run: it inherits nothing from this
#* one that is not passed explicitly. Each sub-build used to receive only
#* CMAKE_BUILD_TYPE and BUILD_SHARED_LIBS, so any flag that has to be applied
#* to the whole program -- a sanitizer, coverage, an ABI or arch switch --
#* reached the sources in this repository and silently missed libast and the
#* ANTLR runtime. A half-instrumented ASan build is the failure mode that
#* motivated this: heap errors were still caught (the runtime interposes
#* malloc globally) but stack and global instrumentation stopped at the
#* pssparser library boundary, and nothing said so.
#*
#* The compiler is forwarded for the same reason. A sub-build that picks a
#* different compiler than this one can pair, say, clang-instrumented objects
#* with the gcc ASan runtime, which fails in ways that look like a bug in the
#* code under test.
#*
#* CXX flags are NOT in this list: libantlr4 needs its own prepended, so each
#* ExternalProject states its CMAKE_CXX_FLAGS line and appends this one.
#********************************************************************
set(FORWARDED_BUILD_ARGS
    "-DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}"
    "-DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}"
    "-DCMAKE_C_FLAGS:STRING=${CMAKE_C_FLAGS}"
    "-DCMAKE_EXE_LINKER_FLAGS:STRING=${CMAKE_EXE_LINKER_FLAGS}"
    "-DCMAKE_SHARED_LINKER_FLAGS:STRING=${CMAKE_SHARED_LINKER_FLAGS}"
    "-DCMAKE_MODULE_LINKER_FLAGS:STRING=${CMAKE_MODULE_LINKER_FLAGS}"
    )

execute_process(COMMAND ${PYTHON} -m ivpm share cmake OUTPUT_VARIABLE IVPM_CMAKE_PATH)
list(APPEND CMAKE_MODULE_PATH ${IVPM_CMAKE_PATH})
message("IVPM_CMAKE_PATH: ${IVPM_CMAKE_PATH} ${CMAKE_MODULE_PATH}")

include(ivpm)

execute_process(
    COMMAND ${PYTHON} -c "import debug_mgr, os; print(os.path.join(os.path.dirname(debug_mgr.__file__), 'share', 'include'))"
    OUTPUT_VARIABLE debug_mgr_INCDIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
execute_process(
    COMMAND ${PYTHON} -c "import debug_mgr, os; print(os.path.dirname(debug_mgr.__file__))"
    OUTPUT_VARIABLE debug_mgr_LIBDIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
message("Set: debug_mgr_INCDIR=${debug_mgr_INCDIR}")
message("Set: debug_mgr_LIBDIR=${debug_mgr_LIBDIR}")

message("Note: CMAKE_INSTALL_PREFIX set to ${CMAKE_INSTALL_PREFIX}")

ExternalProject_Add(libantlr4
    PREFIX antlr4
    SOURCE_DIR "${PACKAGES_DIR}/antlr4-cpp-runtime"
    CMAKE_CACHE_ARGS
      -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_INSTALL_PREFIX}
      -DCMAKE_INTALL_LIBDIR:PATH=${CMAKE_INSTALL_LIBDIR}
      -DCMAKE_INSTALL_BINDIR:PATH=lib
      # ANTLR_CXXFLAGS first: they are what this dependency needs to compile at
      # all (see above), and the build's own flags follow so a later
      # -fsanitize= is not dropped.
      "-DCMAKE_CXX_FLAGS:STRING=${ANTLR_CXXFLAGS} ${CMAKE_CXX_FLAGS}"
      -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
      -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
      -DBUILD_STATIC_LIBS:BOOL=False
      -DCMAKE_OSX_ARCHITECTURES:STRING=${CMAKE_OSX_ARCHITECTURES}
      -DCMAKE_POLICY_VERSION_MINIMUM:STRING=3.5
      ${FORWARDED_BUILD_ARGS}
    )

ExternalProject_Add(AST
	PREFIX pssparser_ast
	SOURCE_DIR "${CMAKE_CURRENT_BINARY_DIR}/pssparser_ast/src"
	DOWNLOAD_COMMAND
        ${PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/gen_ast.py
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_INSTALL_PREFIX}
        -DCMAKE_INSTALL_LIBDIR:PATH=${CMAKE_INSTALL_LIBDIR}
        -DCMAKE_INSTALL_BINDIR:PATH=lib
        -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
        -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
        -DCMAKE_OSX_ARCHITECTURES:STRING=${CMAKE_OSX_ARCHITECTURES}
        "-DCMAKE_CXX_FLAGS:STRING=${CMAKE_CXX_FLAGS}"
        ${FORWARDED_BUILD_ARGS}
	)

# Re-run the generator when the AST specification changes.
#
# ExternalProject steps are stamped, and nothing invalidates the stamp of a
# DOWNLOAD_COMMAND that is really a code generator: the AST was generated once
# and every later build compiled against the headers from that run. An edit to
# ast/*.yaml then failed as a missing accessor on the *generated* class, which
# reads as a mistake in the yaml rather than as a stale build.
#
# GLOB is evaluated at configure time, so *adding* a spec file still needs
# cmake to re-run -- same caveat as pss_stdlib_SRC in src/CMakeLists.txt.
file(GLOB pssparser_ast_SPEC "${CMAKE_CURRENT_SOURCE_DIR}/ast/*.yaml")

ExternalProject_Add_StepDependencies(AST download
	${pssparser_ast_SPEC}
	${CMAKE_CURRENT_SOURCE_DIR}/scripts/gen_ast.py
	)

add_subdirectory(src)


if (ENABLE_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
