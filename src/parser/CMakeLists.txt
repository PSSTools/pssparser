
cmake_minimum_required (VERSION 2.8)

project(parser)

include(ExternalAntlr4Cpp)

add_compile_options(-Wno-attributes)

file(GLOB parser_SRC
	"*.h"
	"*.cpp")

antlr_target(PSS PSS.g4 LEXER PARSER VISITOR
	)

add_library(parser
	${parser_SRC}
	${ANTLR_PSS_OUTPUTS})
		