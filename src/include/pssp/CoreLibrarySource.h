/*
 * CoreLibrarySource.h
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
 */
#pragma once
#include <stdint.h>

namespace pssp {

/**
 * One file of the compiled-in PSS core library.
 *
 * The core library is a single source unit, fileid 0: its files are built
 * one after the other, so each occupies its own band of lines. A location
 * (0, line) belongs to the file whose band holds ``line``, at line
 * ``line - first_line + 1`` of that file.
 */
struct CoreLibrarySource {
    /// File name, such as "addr_reg_pkg.pss".
    const char      *name;
    /// The fileid-0 line on which this file's first line falls.
    int32_t         first_line;
    /// Number of lines in the file.
    int32_t         num_lines;
    /// The file's text, as compiled in.
    const char      *text;
};

}
