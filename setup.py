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
#sys.path.insert(0, os.path.join(os.getcwd(), "../pssast/ext"))
#import pssast_ext

#pss_ext_spec = pssast_ext.ext()
#print("pss_ext_spec: " + str(pss_ext_spec))


pssparser_dir = os.path.dirname(os.path.abspath(__file__))
pythondir = os.path.join(pssparser_dir, "python")
#sys.path.insert(0, extdir)

include_dirs=[]

include_dirs.append(os.path.join(pssparser_dir, "src/include"))

if "CMAKE_BINARY_DIR" in os.environ.keys():
    cmake_binary_dir=os.environ["CMAKE_BINARY_DIR"]
    include_dirs.append(os.path.join(cmake_binary_dir, "pssast/ext"))
    include_dirs.append(os.path.join(cmake_binary_dir, "pssast/ext/"))
    include_dirs.append(os.path.join(cmake_binary_dir, "pssast/src/include"))
    include_dirs.append(os.path.join(pythondir))

library_dirs = [] 

libraries = []

# Create a composite core.pyx file 

#with open(os.path.join(os.getcwd(), "core.pyx"), "w") as out:
#    with open(os.path.join(os.getcwd(), "../pssast/ext/pssast.pyx"), "r") as pssast:
#        out.write(pssast.read())
#    with open(os.path.join(extdir, "core.pyx"), "r") as core:
#        out.write(core.read())
        
sources = []

sources.append(os.path.join(pythondir, "core.pyx"))

# for f in os.listdir(pythondir):
#     if os.path.isfile(os.path.join(pythondir, f)):
#         path_s = os.path.splitext(f)
#         if path_s[1] == ".pyx":
#             print("Add " + f)
# #            sources.append(os.path.join(extdir, f))
#         elif path_s[1] == ".cpp" and not f.endswith("core.cpp"):
#             print("Add " + f)
#             sources.append(os.path.join(pythondir, f))

#for src in pss_ext_spec.sources:
#    path_s = os.path.splitext(src)
#    if path_s[1] == ".cpp":
#        sources.append(src)
                
print("sources=" + str(sources))

# TODO: depending on the platform, perform the link differently
extra_link_args=[]
#extra_link_args.append(os.path.join(os.getcwd(), "../antlr4/lib/libantlr4-runtime.a"))

ast_ext_srcs = [os.path.join(pythondir, "pssast.pyx")],
ast_ext = Extension(
    "pssparser.pssast", 
    [
        os.path.join(pythondir, "pssast.pyx"),
        os.path.join(pythondir, "PyBaseVisitor.cpp")
    ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
    language="c++")
ext = Extension(
    "pssparser.core", 
    sources,
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
    language="c++")

# sources = []
# include_dirs = [os.path.join(extdir, "pyiostream")]
# library_dirs = []
# libraries = []
# extra_link_args=[]

# pyiostream_ext = os.path.join(extdir, "pssparser", "iostream")
# for f in os.listdir(pyiostream_ext):
#     if os.path.isfile(os.path.join(extdir, f)):
#         path_s = os.path.splitext(f)
#         if path_s[1] == ".pyx":
#             sources.append(os.path.join(pyiostream_ext, f))
#         elif path_s[1] == ".cpp":
#             if not os.path.isfile(os.path.join(pyiostream_ext, path_s[0] + ".pyx")):
#                 sources.append(os.path.join(pyiostream_ext, f))
# 
# pyiostream = Extension(
#     "pssparser.iostream",
#     sources,
#     include_dirs=include_dirs,
#     library_dirs=library_dirs,
#     libraries=libraries,
#     extra_link_args=extra_link_args,
#     language="c++")

#extensions=[ext, pyiostream]
extensions=[ast_ext, ext]

setup(
    name="pssparser",
    version="0.0.1",
    author="Matthew Ballance",
    author_email="matt.ballance@gmail.com",
    description="Provides a PSS parser and related tools",
    packages=find_namespace_packages(where=pythondir),
    package_dir={'' : pythondir },
    ext_modules=cythonize(extensions)
    )
