cmake_minimum_required (VERSION 2.8)

project(pssparser)

include(ExternalProject)

list(APPEND CMAKE_MODULE_PATH 
	${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-cpp-runtime/cmake)

# Some include	
include_directories(${CMAKE_BINARY_DIR}/pss_ast/include/project_ast)

set(ANTLR_EXECUTABLE ${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-tools.jar)
set(ANTLR4_JAR_LOCATION ${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-tools.jar)

if (WIN32)
  set(PYTHON ${CMAKE_CURRENT_SOURCE_DIR}/packages/python/Scripts/python.exe)
else()
  set(PYTHON ${CMAKE_CURRENT_SOURCE_DIR}/packages/python/bin/python)
endif()

find_package(ANTLR REQUIRED)

ExternalProject_Add(LIBANTLR4
    PREFIX antlr4
    SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-cpp-runtime"
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/antlr4
	-DCMAKE_CXX_FLAGS:STRING=-Wno-attributes
    )
    
ExternalProject_Add(pss_ast
	PREFIX pss_ast
	SOURCE_DIR "${CMAKE_CURRENT_BINARY_DIR}/pss_ast/src"
	DOWNLOAD_COMMAND ${PYTHON} -m astbuilder -astdir ${CMAKE_CURRENT_SOURCE_DIR}/ast -license ${CMAKE_CURRENT_SOURCE_DIR}/scripts/copyright.cpp
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/pss_ast
	)

add_subdirectory(src/parser)

