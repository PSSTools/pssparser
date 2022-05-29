#****************************************************************************
#* CMakeLists.txt
#****************************************************************************
cmake_minimum_required (VERSION 2.8)

include(ExternalAntlr4Cpp)

if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_compile_options(-Wno-attributes)
  add_compile_options(-fPIC)
else()
  add_compile_options(-DANTLR4CPP_STATIC)
endif()

include_directories(
    ${CMAKE_BINARY_DIR}/antlr4/include/antlr4-runtime
    ${PACKAGES_DIR}/antlr4-cpp-runtime/runtime/src
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSLexer
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSSParser
    ${CMAKE_BINARY_DIR}/pssast/src/include
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    )

antlr_target(PSSLexer PSSLexer.g4 LEXER)
antlr_target(PSSParser PSSParser.g4 PARSER 
             DEPENDS_ANTLR PSSLexer
             COMPILE_FLAGS -lib ${ANTLR_PSSLexer_OUTPUT_DIR}
             VISITOR LISTENER)

#********************************************************************
#* pssparser
#********************************************************************
file(GLOB pssparser_SRC
	"*.h"
	"*.cpp")
add_library(pssparser
	${pssparser_SRC}
	${ANTLR_PSSParser_OUTPUTS}
	${ANTLR_PSSLexer_OUTPUTS})

install(TARGETS pssparser
    DESTINATION lib
    EXPORT pssparser-targets)
    
add_dependencies(pssparser AST libantlr4)
	
#add_library(pssformatter
#	${parser_SRC}
#	${ANTLR_PSS_OUTPUTS})
	
#add_executable(pssformat
#	apps/pssformat_main.cpp)

#target_link_libraries(pssformat
#	pssparser
#	antlr4-runtime)
	
	
#add_dependencies(pssformat
#	libantlr4)
  
#add_dependencies(parser gen_pss_parser)
		
