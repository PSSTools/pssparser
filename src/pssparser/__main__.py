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
