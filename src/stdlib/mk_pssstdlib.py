
import io
import sys
import os

copyright = """
/**
 * pss_stdlib.h
 *
 * Contains source for PSS standard-library types
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
"""

print("mk_pssstdlib.py")


def write_if_changed(path, content):
    """Write *content* to *path* only when it differs from what is there.

    Kept local rather than imported from astbuilder: this script is also run
    by the native build, and standalone is what makes that safe.
    """
    try:
        with open(path, "r") as fp:
            if fp.read() == content:
                return False
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        pass
    with open(path, "w") as fp:
        fp.write(content)
    return True


def main():
    pss_stdlib_dir = os.path.dirname(os.path.abspath(__file__))

    # Built in memory rather than streamed to the destination so that the
    # result can be compared against what is already there. The wasm build
    # runs this at cmake *configure* time, and an explicit `cmake -S -B`
    # always re-configures -- so an unconditional write made pss_stdlib.h
    # newer than every object that includes it, and a no-op refresh became a
    # full rebuild of the parser.
    out = io.StringIO()

    out.write(copyright)
    out.write("#include \"pssp/CoreLibrarySource.h\"\n\n")

    # Sorted, because os.listdir order is filesystem-dependent. Without this
    # the file's *content* varies between runs, which is both a
    # reproducibility problem and enough to defeat the comparison below.
    #
    # The files are built as one unit (fileid 0), one after the other, so each
    # occupies its own band of lines; pss_stdlib_files records the bands.
    # The raw string starts directly with the file's text: a newline after
    # `R"(` would shift every line by one.
    files = []
    first_line = 1
    for f in sorted(os.listdir(pss_stdlib_dir)):
        base,ext = os.path.splitext(f)
        if ext == ".pss":
            with open(os.path.join(pss_stdlib_dir, f), "r") as fp:
                data = fp.read()
            if not data.endswith("\n"):
                data += "\n"
            num_lines = data.count("\n")
            files.append((f, base, first_line, num_lines))
            first_line += num_lines
            out.write("static const char *%s = R\"(" % base)
            out.write(data)
            out.write(")\";\n")
            out.write("\n")

    out.write("static const pssp::CoreLibrarySource pss_stdlib_files[] = {\n")
    for name, base, first, num in files:
        out.write("    {\"%s\", %d, %d, %s},\n" % (name, first, num, base))
    out.write("    {0, 0, 0, 0}\n")
    out.write("};\n")
    out.write("\n")

    content = out.getvalue()

    if len(sys.argv) > 1 and sys.argv[1] != "-":
        write_if_changed(sys.argv[1], content)
    else:
        sys.stdout.write(content)

if __name__ == "__main__":
    main()

