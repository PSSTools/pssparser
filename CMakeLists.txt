cmake_minimum_required (VERSION 2.8)

project(pssparser)

include(ExternalProject)

if (NOT PACKAGES_DIR)
  set(PACKAGES_DIR ${CMAKE_SOURCE_DIR}/packages)
endif()

list(APPEND CMAKE_MODULE_PATH ${PACKAGES_DIR}/antlr4-cpp-runtime/cmake)

# Some include	
include_directories(${CMAKE_BINARY_DIR}/pss_ast/include/project_ast)

link_directories(
	${CMAKE_BINARY_DIR}/antlr4/lib
	)

set(ANTLR_EXECUTABLE ${PACKAGES_DIR}/antlr4-tools.jar)
set(ANTLR4_JAR_LOCATION ${PACKAGES_DIR}/antlr4-tools.jar)

if (WIN32)
  set(PYTHON ${PACKAGES_DIR}/python/Scripts/python.exe)
else()
  set(PYTHON ${PACKAGES_DIR}/python/bin/python)
endif()

find_package(ANTLR REQUIRED)

ExternalProject_Add(LIBANTLR4
    PREFIX antlr4
    SOURCE_DIR "${PACKAGES_DIR}/antlr4-cpp-runtime"
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/antlr4
	-DCMAKE_CXX_FLAGS:STRING=-Wno-attributes
	-DCMAKE_C_COMPILER:STRING=${CMAKE_C_COMPILER}
	-DCMAKE_CXX_COMPILER:STRING=${CMAKE_CXX_COMPILER}
	-DCMAKE_C_COMPILER_ID:STRING=${CMAKE_C_COMPILER_ID}
	-DCMAKE_CXX_COMPILER_ID:STRING=${CMAKE_CXX_COMPILER_ID}
	-DCMAKE_SYSTEM_NAME:STRING=${CMAKE_SYSTEM_NAME}
    )
    
ExternalProject_Add(pss_ast
	PREFIX pss_ast
	SOURCE_DIR "${CMAKE_CURRENT_BINARY_DIR}/pss_ast/src"
	DOWNLOAD_COMMAND ${PYTHON} -m astbuilder -astdir ${CMAKE_CURRENT_SOURCE_DIR}/ast -license ${CMAKE_CURRENT_SOURCE_DIR}/scripts/copyright.cpp
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/pss_ast
	)

add_subdirectory(src)


