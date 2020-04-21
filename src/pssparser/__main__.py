
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

'''
Created on Feb 16, 2020

@author: ballance
'''
import argparse
import os
import sys

from antlr4.InputStream import InputStream
from pssparser.cu_parser import CUParser

_verbosity = 0

def verbose(msg, *args):
    if _verbosity > 0:
        print(msg % args)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", action="store_true")
    parser.add_argument("-link", action="store_true",
        help="Resolve symbol references")
    parser.add_argument("files", nargs="+")
   
    return parser

def main():
    global _verbosity
    compile_units = []
    parser = get_parser()
    
    argv = []
    i=1
    while i < len(sys.argv):
        arg = sys.argv[i]
        argv.append(arg)
        i+=1

    args = parser.parse_args(argv)

    if args.v:
        _verbosity = 1
    
    
    for f in args.files:
        if not os.path.isfile(f):
            print("Error: file \"" + f + "\" does not exist")
            sys.exit(1)

        with open(f, "r") as fp:            
            input_stream = InputStream(fp.read())
            
        verbose("Parsing file %s", f)
        parser = CUParser(input_stream, f)
        cu = parser.parse()
        
        if len(cu.markers) > 0:
            for m in cu.markers:
                print("Error: " + m.msg)
            sys.exit(1)
            
        compile_units.append(cu)
        
    if args.link:
        print("Error: link not currently supported")
        sys.exit(1)
            
        
    

if __name__ == "__main__":
    main()
