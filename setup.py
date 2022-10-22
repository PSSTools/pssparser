#*****************************************************************************
#* setup.py
#*
#* pssparser Python extension setup file
#*****************************************************************************

import os
import sys
import subprocess
import sysconfig
import shutil

from setuptools import Extension, setup, find_namespace_packages
from setuptools.command.build_ext import build_ext as _build_ext
from distutils.file_util import copy_file
from Cython.Build import cythonize

version="0.0.1"

# Bring in the Python file with settings for the Python extension
#sys.path.insert(0, os.path.join(os.getcwd(), "../pssast/ext"))
#import pssast_ext

#pss_ext_spec = pssast_ext.ext()
#print("pss_ext_spec: " + str(pss_ext_spec))

if "-DDEBUG" in sys.argv:
    sys.argv.remove("-DDEBUG")
    CMAKE_BUILD_TYPE="Debug"
    _DEBUG = True
else:
    CMAKE_BUILD_TYPE="Release"
    _DEBUG = False

pssparser_dir = os.path.dirname(os.path.abspath(__file__))
pythondir = os.path.join(pssparser_dir, "python")

if os.path.isdir(os.path.join(pssparser_dir, "packages")):
    print("Pacakges are inside this directory")
    packages_dir = os.path.join(pssparser_dir, "packages")
else:
    parent = os.path.dirname(pssparser_dir)

    if os.path.isdir(os.path.join(parent, "pssparser")):
        print("pssparser is a peer")
        packages_dir = parent
    else:
        raise Exception("Unexpected source layout")

#sys.path.insert(0, extdir)

cwd = os.getcwd()
if not os.path.isdir(os.path.join(cwd, "build")):
    os.makedirs(os.path.join(cwd, "build"))

#if not os.path.isdir(os.path.join(libvsc_dir, "python/libvsc")):
#    os.makedirs(os.path.join(tblink_vsc, "python/libvsc"))

env = os.environ.copy()
python_bindir = os.path.dirname(sys.executable)
print("python_bindir: %s" % str(python_bindir))

if "PATH" in env.keys():
    env["PATH"] = python_bindir + os.pathsep + env["PATH"]
else:
    env["PATH"] = python_bindir

# Run configure...
result = subprocess.run(
    ["cmake", 
     pssparser_dir,
     "-GNinja",
     "-DCMAKE_BUILD_TYPE=%s" % CMAKE_BUILD_TYPE,
     "-DPACKAGES_DIR=%s" % packages_dir,
     ],
    cwd=os.path.join(cwd, "build"),
    env=env)

if result.returncode != 0:
    raise Exception("cmake configure failed")

result = subprocess.run(
    ["ninja",
     "-j",
     "%d" % os.cpu_count()
     ],
    cwd=os.path.join(cwd, "build"),
    env=env)
if result.returncode != 0:
    raise Exception("build failed")

#********************************************************************
#* Copy over required files
#********************************************************************
builddir = os.path.join(cwd, "build")
file_m = {
    os.path.join(builddir, "pssast/ext/pssast_decl.pxd") : os.path.join(pythondir, "pssparser/pssast_decl.pxd"),
    os.path.join(builddir, "pssast/ext/pssast.pxd") : os.path.join(pythondir, "pssparser/pssast.pxd"),
    os.path.join(builddir, "pssast/ext/pssast.pyx") : os.path.join(pythondir, "pssast.pyx"),
    os.path.join(builddir, "pssast/ext/PyBaseVisitor.h") : os.path.join(pythondir, "PyBaseVisitor.h")
}

for src,dst in file_m.items():
    shutil.copy(src, dst)

extra_compile_args = sysconfig.get_config_var('CFLAGS').split()
extra_compile_args = []
#extra_compile_args += ["-std=c++11", "-Wall", "-Wextra"]
if _DEBUG:
#    extra_compile_args += ["-g", "-O0", "-DDEBUG=%s" % _DEBUG_LEVEL, "-UNDEBUG"]
    extra_compile_args += ["-g", "-O0", "-UNDEBUG"]
else:
    extra_compile_args += ["-DNDEBUG", "-O3"]

class build_ext(_build_ext):
    def run(self):
        super().run()

    # Needed for Windows to not assume python module (generate interface in def file)
    def get_export_symbols(self, ext):
        return None

    def copy_extensions_to_source(self):
        """ Like the base class method, but copy libs into proper directory in develop. """
        print("copy_extensions_to_source")
        super().copy_extensions_to_source()

        build_py = self.get_finalized_command("build_py")
        
        ext = self.extensions[0]
        fullname = self.get_ext_fullname(ext.name)
        filename = self.get_ext_filename(fullname)
        modpath = fullname.split(".")
        package = ".".join(modpath[:-1])
        package_dir = build_py.get_package_dir(package)

        copy_file(
            os.path.join(cwd, "build", "src", "libpssparser.so"),
            os.path.join(package_dir, "libpssparser.so"))
        copy_file(
            os.path.join(cwd, "build", "antlr4", "libantlr4-runtime.so"),
            os.path.join(package_dir, "libantlr4-runtime.so"))
                
        dest_filename = os.path.join(package_dir, filename)
        
        print("package_dir: %s dest_filename: %s" % (package_dir, dest_filename))
        
        return

include_dirs=[]

include_dirs.append(os.path.join(pssparser_dir, "src/include"))

build_dir = os.path.join(pssparser_dir, "build")

include_dirs.append(build_dir)
include_dirs.append(os.path.join(build_dir, "pssast/ext"))
include_dirs.append(os.path.join(build_dir, "pssast/src/include"))

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
    packages=find_namespace_packages(where=pythondir),
    package_dir={'' : pythondir },
    version=version,
    author="Matthew Ballance",
    author_email="matt.ballance@gmail.com",
    description="Provides a PSS parser and related tools",
    long_description="""
    PSSParser
    """,
    ext_modules=cythonize(extensions),
    cmdclass={'build_ext': build_ext}
    )
