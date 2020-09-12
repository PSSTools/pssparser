cmake_minimum_required (VERSION 2.8)

include(ExternalProject)

list(APPEND CMAKE_MODULE_PATH 
	${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-cpp-runtime/cmake)

set(ANTLR_EXECUTABLE ${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-tools.jar)
set(ANTLR4_JAR_LOCATION ${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-tools.jar)

#find_package(antlr4-generator REQUIRED)
#find_package(antlr4-runtime REQUIRED)
#find_package(ANTLR REQUIRED)

ExternalProject_Add(LIBANTLR4
    PREFIX antlr4
    SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-cpp-runtime"
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/antlr4
    )

#antlr_target(PSSParser src/PSS.g4 PARSER
#	package antlrcpptest)

#include_directories(
#	${ANTLR_PSSParser_OUTPUT_DIR}
#	${CMAKE_CURRENT_BINARY_DIR}/antlr4/include/antlr4-runtime
#	)

#add_executable(demo 
#	${ANTLR_PSSParser_OUTPUT_DIR}/src/PSSLexer.cpp
#	${ANTLR_PSSParser_OUTPUT_DIR}/src/PSSParser.cpp)

