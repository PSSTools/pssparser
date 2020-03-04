'''
Created on Feb 16, 2020

@author: ballance
'''
import argparse


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", action="store_const", const=True, default=False)
    parser.add_argument("files", action="append")
   
    return parser

def main():
    parser = get_parser()

    args = parser.parse_args()
    
    for f in args.files:
        print("f=" + str(f))
    
    
    pass

