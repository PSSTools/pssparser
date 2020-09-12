
include(ExternalProject)

ExternalProject_Add(LIBANTLR4
    PREFIX antlr4
    SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/packages/antlr4-cpp-runtime"
    CMAKE_CACHE_ARGS
        -DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/antlr4
    )
