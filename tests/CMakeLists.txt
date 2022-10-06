
cmake_minimum_required(VERSION 2.8.8)

ExternalProject_Add(GTEST
	PREFIX gtest
        SOURCE_DIR "${PACKAGES_DIR}/gtest"
        CMAKE_CACHE_ARGS
          -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_BINARY_DIR}/gtest
	  -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
	  -DBUILD_SHARED_LIBS:BOOL=${BUILD_SHARED_LIBS}
    )

file(GLOB TEST_SRCS 
	"src/*.cpp" 
	"src/*.h")

link_directories(
	${CMAKE_BINARY_DIR}/gtest/lib
	${CMAKE_BINARY_DIR}/gtest/lib64
	${CMAKE_BINARY_DIR}/antlr4/lib
	${CMAKE_BINARY_DIR}/pssparser
	${CMAKE_BINARY_DIR}/pssast/lib
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
	${CMAKE_BINARY_DIR}/pssast/src/include
	${CMAKE_CURRENT_SOURCE_DIR}/../src
	${CMAKE_CURRENT_SOURCE_DIR}/../src/include
)

message(STATUS "CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}")
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    message(STATUS "Taking debug libs")
    list(APPEND PSSPARSER_TESTMAIN_LIBS gtestd gtest_maind pssparser pssast)
else()
    message(STATUS "Taking release libs")
    list(APPEND PSSPARSER_TESTMAIN_LIBS gtest gtest_main pssparser pssast)
endif()

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


