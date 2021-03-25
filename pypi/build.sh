#!/usr/bin/env bash
set -e -o pipefail

export PATH=/opt/python/cp39-cp39/bin:${PATH}

mkdir /build
cp -r /pssparser /build

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

