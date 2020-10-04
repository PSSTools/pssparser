
cmake_minimum_required (VERSION 2.8)

project(parser)

include(ExternalAntlr4Cpp)

add_compile_options(-Wno-attributes)
include_directories(
    ${CMAKE_BINARY_DIR}/antlr4/include/antlr4-runtime
    ${CMAKE_CURRENT_BINARY_DIR}/antlr4cpp_generated_src/PSS)

file(GLOB parser_SRC
	"*.h"
	"*.cpp")

antlr_target(PSS PSS.g4 LEXER PARSER VISITOR
	)

# Wrap generation of ANTLR code in a custom target	
#add_custom_target(
#    gen_pss_parser
#    DEPENDS ${ANTLR_PSS_OUTPUTS})

add_library(pssparser
	${parser_SRC}
	${ANTLR_PSS_OUTPUTS})

add_dependencies(pssparser 
	libantlr4
	pss_ast)

install(TARGETS pssparser
    DESTINATION lib
    EXPORT pssparser-targets)
    