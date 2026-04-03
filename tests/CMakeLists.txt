
cmake_minimum_required(VERSION 3.10)

file(GLOB TEST_SRCS
	"src/*.cpp"
	"src/*.h")

if(TEST_SRCS)

ExternalProject_Add(GTEST
	PREFIX gtest
        SOURCE_DIR "${PACKAGES_DIR}/gtest"
        CMAKE_CACHE_ARGS
          -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_BINARY_DIR}/gtest
	  -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
	  -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
    )

set(CMAKE_INSTALL_RPATH $ORIGIN/../lib)

link_directories(
	${CMAKE_BINARY_DIR}/gtest/lib
	${CMAKE_BINARY_DIR}/gtest/lib64
	${CMAKE_BINARY_DIR}/lib
	${CMAKE_BINARY_DIR}/lib64
	${CMAKE_BINARY_DIR}/src
	${CMAKE_BINARY_DIR}/pssparser_ast/lib
    "${debug_mgr_LIBDIR}"
	)

set(CompilerFlags
        CMAKE_CXX_FLAGS
        CMAKE_CXX_FLAGS_DEBUG
        CMAKE_CXX_FLAGS_RELEASE
        CMAKE_C_FLAGS
        CMAKE_C_FLAGS_DEBUG
        CMAKE_C_FLAGS_RELEASE
        )
foreach(CompilerFlag ${CompilerFlags})
  string(REPLACE "/MD" "/MT" ${CompilerFlag} "${${CompilerFlag}}")
  string(REPLACE "/MDd" "/MTd" ${CompilerFlag} "${${CompilerFlag}}")
endforeach()

#********************************************************************
#* GoogleTest unit tests
#********************************************************************
add_executable(pssparser_testmain ${TEST_SRCS})

set_property(TARGET pssparser_testmain PROPERTY
  MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

add_dependencies(pssparser_testmain GTEST AST libantlr4)
target_include_directories(pssparser_testmain PRIVATE
	${CMAKE_BINARY_DIR}
	${CMAKE_BINARY_DIR}/gtest/include
	${PACKAGES_DIR}/gtest/googletest/include
	${CMAKE_BINARY_DIR}/pssparser_ast/src/include
	${CMAKE_CURRENT_SOURCE_DIR}/../src
	${CMAKE_CURRENT_SOURCE_DIR}/../src/include
    "${debug_mgr_INCDIR}"
)

message(STATUS "CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}")
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    message(STATUS "Taking debug libs")
    if (WIN32)
        list(APPEND PSSPARSER_TESTMAIN_LIBS gtestd gtest_maind)
    else()
        list(APPEND PSSPARSER_TESTMAIN_LIBS gtest gtest_main)
    endif()
else()
    message(STATUS "Taking release libs")
    list(APPEND PSSPARSER_TESTMAIN_LIBS gtest gtest_main)
endif()

list(APPEND PSSPARSER_TESTMAIN_LIBS pssparser ast debug-mgr)

if (WIN32)
	if (BUILD_SHARED_LIBS)
		list(APPEND PSSPARSER_TESTMAIN_LIBS antlr4-runtime)
	else()
		list(APPEND PSSPARSER_TESTMAIN_LIBS antlr4-runtime-static)
	endif()
else()
	list(APPEND PSSPARSER_TESTMAIN_LIBS antlr4-runtime pthread)
endif()

target_link_libraries(pssparser_testmain ${PSSPARSER_TESTMAIN_LIBS})

add_test(
	NAME unit
	COMMAND ${CMAKE_BINARY_DIR}/tests/pssparser_testmain)

else()
    message(STATUS "No C++ test sources found in tests/src/, skipping test target")
endif()
