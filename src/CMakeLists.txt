#****************************************************************************
#* CMakeLists.txt
#****************************************************************************
cmake_minimum_required (VERSION 3.5)

include(ExternalAntlr4Cpp)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_compile_options(-Wno-attributes)
  add_compile_options(-fPIC)
else()
  add_compile_options(-DANTLR4CPP_STATIC)
endif()

if (MSVC)
  # The ANTLR-generated PSSParser/PSSLexer translation units blow past the
  # default 64k section limit, and the .g4-derived sources contain UTF-8.
  add_compile_options(/bigobj /utf-8)
endif()

set(CMAKE_INSTALL_RPATH "$ORIGIN;$ORIGIN/../lib64")

include_directories(
    ${CMAKE_BINARY_DIR}/antlr4/include/antlr4-runtime
    ${PACKAGES_DIR}/antlr4-cpp-runtime/runtime/src
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSLexer
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSParser
    ${CMAKE_BINARY_DIR}/pssparser_ast/src/include
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    "${debug_mgr_INCDIR}"
    )

link_directories(
	${CMAKE_BINARY_DIR}/lib
	${CMAKE_BINARY_DIR}/lib64
	)

antlr_target(PSSLexer PSSLexer.g4 LEXER)
antlr_target(PSSParser PSSParser.g4 PARSER
             DEPENDS_ANTLR PSSLexer
             COMPILE_FLAGS -lib ${ANTLR_PSSLexer_OUTPUT_DIR}
             VISITOR LISTENER)

#********************************************************************
#* pssparser library
#********************************************************************
file(GLOB pssparser_SRC
	"*.h"
	"*.cpp")
add_library(pssparser SHARED
	${pssparser_SRC}
    pss_stdlib.h
	${ANTLR_PSSParser_OUTPUTS}
	${ANTLR_PSSLexer_OUTPUTS})

install(TARGETS pssparser
    EXPORT pssparser-targets
    RUNTIME DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/include/pssp" # source directory
    DESTINATION "include" # target directory
    FILES_MATCHING # install only matched files
    PATTERN "*.h" # select header files
)

add_dependencies(pssparser AST libantlr4)

if (WIN32)
	if (BUILD_SHARED_LIBS)
		list(APPEND PSSPARSER_LIBS antlr4-runtime)
	else()
		list(APPEND PSSPARSER_LIBS antlr4-runtime-static)
	endif()
else()
	list(APPEND PSSPARSER_LIBS antlr4-runtime pthread)
endif()

target_link_libraries(pssparser ${PSSPARSER_LIBS})

# Selects the dllexport side of PSSPARSER_API in pssp/FactoryExt.h.  PRIVATE:
# consumers of the installed headers must see the dllimport side.
target_compile_definitions(pssparser PRIVATE PSSPARSER_BUILD_DLL)
set_target_properties(pssparser PROPERTIES SKIP_BUILD_RPATH TRUE)

file(GLOB pss_stdlib_SRC "stdlib/*.pss")

add_custom_command(
    OUTPUT pss_stdlib.h
    DEPENDS ${pss_stdlib_SRC}
    COMMAND ${PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/stdlib/mk_pssstdlib.py
        ${CMAKE_CURRENT_BINARY_DIR}/pss_stdlib.h
)
