/**
 * Loader.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author: 
 */
#pragma once
#include <algorithm>
#include <string>
#include "pssp/IFactory.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

#ifdef _WIN32
#error unimplemented
#else
typedef void *lib_handle_t;
typedef void *sym_handle_t;
static lib_handle_t load_library(const char *path) {
    return dlopen(path, RTLD_LAZY);
}
static sym_handle_t find_symbol(lib_handle_t lib, const char *sym) {
    return dlsym(lib, sym);
}
static const char *last_error() {
    return dlerror();
}
#endif


static pssp::IFactory *loadPssParserFactory(const char *path) {
    typedef pssp::IFactory *(*get_f)();
    std::string path_s = path;

    // Normalize Windows->Unix paths
    std::replace(path_s.begin(), path_s.end(), '\\', '/');

    int last_ps = path_s.rfind('/');
    std::string libdir;
    if (last_ps != -1) {
        libdir = path_s.substr(0, last_ps+1);
    }

    // // Before we can load the library parser library, we need to
    // // load the dependencies
    // std::string libantlr_rt = libdir + "libantlr4-runtime.so";

    // lib_handle_t antlr_h = load_library(libantlr_rt.c_str());

    // if (!antlr_h) {
    //     return 0;
    // }

    lib_handle_t hndl = load_library(path);

    // if (!hndl) {
    //     return 0;
    // }

    sym_handle_t sym = dlsym(hndl, "pssparser_getFactory");
    if (!sym) {
        return 0;
    }

    get_f func = (get_f)sym;

    return func();
}

