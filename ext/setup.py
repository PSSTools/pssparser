#*****************************************************************************
#* setup.py
#*
#* pssparser Python extension setup file
#*****************************************************************************

import os
import sys

from setuptools import Extension, setup, find_namespace_packages
from Cython.Build import cythonize

# Bring in the Python file with settings for the Python extension
sys.path.insert(0, os.path.join(os.getcwd(), "../pssast/ext"))
import pssast_ext

pss_ext_spec = pssast_ext.ext()

print("pss_ext_spec: " + str(pss_ext_spec))


extdir = os.path.dirname(os.path.abspath(__file__))
pssparserdir = os.path.dirname(extdir)
include_dirs=[]
include_dirs.append(extdir)
include_dirs.append(os.path.join(pssparserdir, "src"))
include_dirs.append(os.path.join(os.getcwd(), "../pssast/include/pssast"))
include_dirs.append(os.path.join(os.getcwd(), "../pssast/ext"))

library_dirs = [] 
library_dirs.append(os.path.join(os.getcwd(), "../src"))
library_dirs.append(os.path.join(os.getcwd(), "../pssast/lib"))
library_dirs.append(os.path.join(os.getcwd(), "../antlr4/lib"))

libraries = []
libraries.append("pssparser")
libraries.append("pssast")
#libraries.append("antlr4-runtime")

sources = []

for f in os.listdir(extdir):
    if os.path.isfile(os.path.join(extdir, f)):
        path_s = os.path.splitext(f)
        if path_s[1] == ".pyx":
            print("Add " + f)
            sources.append(os.path.join(extdir, f))
        elif path_s[1] == ".cpp":
            if not os.path.isfile(os.path.join(extdir, path_s[0] + ".pyx")):
                print("Add " + f)
                sources.append(os.path.join(extdir, f))
                
sources.extend(pss_ext_spec.sources)
                
print("sources=" + str(sources))

# TODO: depending on the platform, perform the link differently
extra_link_args=[]
extra_link_args.append(os.path.join(os.getcwd(), "../antlr4/lib/libantlr4-runtime.a"))

ext = Extension(
    "pssparser.core", 
    sources,
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
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
