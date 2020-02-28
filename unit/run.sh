#!/bin/sh

cwd=`pwd`
root=`cd $cwd/.. ; pwd`
export PYTHONPATH=$root/src:$root/gen-src

$root/packages/python/bin/python3 -m unittest 

