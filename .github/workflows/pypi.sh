#!/usr/bin/env bash
set -e -o pipefail

yum install -y libuuid-devel
yum install -y wget

# Install a JRE
yum install -y java-1.8.0-openjdk-devel

# Install PyPy
wget https://downloads.python.org/pypy/pypy3.7-v7.3.3-linux64.tar.bz2
tar xvjf pypy3.7-v7.3.3-linux64.tar.bz2

cwd=`pwd`
#$cwd/

/opt/python/cp35-cp35m/bin/pip install cython wheel twine
/opt/python/cp36-cp36m/bin/pip install cython wheel twine
/opt/python/cp37-cp37m/bin/pip install cython wheel twine
/opt/python/cp38-cp38/bin/pip install cython wheel twine
/opt/python/cp39-cp39/bin/pip install cython wheel twine ivpm

export PATH=/opt/python/cp39-cp39/bin:${PATH}

mkdir /build
cp -r /github/workspace /build/pssparser

cd /build/pssparser
rm -rf build packages

# Fetch packages
ivpm update -r requirements_ci.txt

# Now, perform a series of build -- one for each Python version

mkdir build
cd build

for py in cp35-cp35m cp36-cp36m cp37-cp37m cp38-cp38 cp39-cp39; do
    export EXT_PYTHON=/opt/python/${py}/bin/python
    cmake ..
    make
done

# Copy the dist results back
cp -r ext/dist /github/workspace

