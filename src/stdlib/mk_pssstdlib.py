
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

def main():
    pss_stdlib_dir = os.path.dirname(os.path.abspath(__file__))

    out = None

    if len(sys.argv) > 1:
        if sys.argv[1] == "-":
            out = sys.stdout
        else:
            out = open(sys.argv[1], "w")
    else:
        out = sys.stdout

    out.write(copyright)

    files = []
    for f in os.listdir(pss_stdlib_dir):
        base,ext = os.path.splitext(f)
        if ext == ".pss":
            files.append(base)
            out.write("static const char *%s = R\"(\n" % base)
            with open(os.path.join(pss_stdlib_dir, f), "r") as fp:
                data = fp.read()
                out.write(data)
            out.write(")\";\n")
            out.write("\n")

    out.write("static const char *pss_stdlib[] = {\n")
    for file in files:
        out.write("    %s,\n" % file)
    out.write("    0\n")
    out.write("};\n")
    out.write("\n")

    if out is not sys.stdout:
        out.close()

    pass

if __name__ == "__main__":
    main()

