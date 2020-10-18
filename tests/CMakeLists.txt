
cmake_minimum_required(VERSION 2.8.8)

file(GLOB TEST_SRCS 
	"src/*.cpp" 
	"src/*.h")

link_directories(
	${CMAKE_BINARY_DIR}/googletest/lib
	${CMAKE_BINARY_DIR}/googletest/lib64
	${CMAKE_BINARY_DIR}/antlr/lib
	${CMAKE_BINARY_DIR}/pssparser
	${CMAKE_BINARY_DIR}/pss_ast/lib
	)

#********************************************************************
#* GoogleTest unit tests
#********************************************************************
add_executable(pssparser_testmain ${TEST_SRCS})
add_dependencies(pssparser_testmain googletest)
target_include_directories(pssparser_testmain PRIVATE
	${CMAKE_BINARY_DIR}/googletest/include
	${PACKAGES_DIR}/googletest/googletest/include
	${CMAKE_CURRENT_SOURCE_DIR}/../src)
target_link_libraries(pssparser_testmain 
	gtest 
	gtest_main 
	pssparser
	project_ast
	antlr4-runtime
	pthread)

add_test(
	NAME unit
	COMMAND ${CMAKE_BINARY_DIR}/tests/pssparser_testmain)


