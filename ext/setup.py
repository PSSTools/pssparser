#*****************************************************************************
#* setup.py
#*
#* pssparser Python extension setup file
#*****************************************************************************

import os
import sys

from setuptools import Extension, setup, find_namespace_packages
from Cython.Build import cythonize


extdir = os.path.dirname(os.path.abspath(__file__))
pssparserdir = os.path.dirname(extdir)
include_dirs=[]
include_dirs.append(extdir)
include_dirs.append(os.path.join(pssparserdir, "src"))
include_dirs.append(os.path.join(os.getcwd(), "../pssast/include/pssast"))

library_dirs = [] 
library_dirs.append(os.path.join(os.getcwd(), "../src"))
library_dirs.append(os.path.join(os.getcwd(), "../pssast/lib"))

libraries = []
libraries.append("pssparser")
libraries.append("pssast")

ext = Extension(
    "pssparser.core", [
        os.path.join(extdir, "pssparser.pyx")
        ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    language="c++")

extensions=[ext]

setup(
    name="pypssparser",
    version="0.0.1",
    author="Matthew Ballance",
    author_email="matt.ballance@gmail.com",
    description="Provides a PSS parser and related tools",
    packages=find_namespace_packages(where=os.path.join(extdir, 'src')),
    package_dir={'' : os.path.join(extdir,'src')},
    ext_modules=cythonize(extensions)
    )
