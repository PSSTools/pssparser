'''
Created on Mar 23, 2021

@author: mballance
'''
import argparse

def getparser():
    parser = argparse.ArgumentParser()
    
    return parser

def main():
    parser = getparser()
    
    args = parser.parse_args()
    pass

if __name__ == "__main__":
    main()

    