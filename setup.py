#*****************************************************************************
#* setup.py
#*
#* pssparser Python extension setup file
#*****************************************************************************
import os
import sys
import platform
from setuptools import Extension, setup, find_namespace_packages

proj_dir = os.path.dirname(os.path.abspath(__file__))
pythondir = os.path.join(proj_dir, "python")

def _get_version():
    version_file = os.path.join(proj_dir, "python", "pssparser", "__version__.py")
    glb = {}
    with open(version_file) as f:
        exec(f.read(), glb)
    return glb["_pkg_version"]

version = _get_version()

isSrcBuild = False

try:
    from ivpm.setup import setup
    isSrcBuild = os.path.isdir(os.path.join(proj_dir, "src"))
    print("pssparser: isSrcBuild: %s" % str(isSrcBuild))
except ImportError as e:
    from setuptools import setup
    print("pssparser: not IVPM build (Falling back): %s" % str(e))

include_dirs = []

if isSrcBuild:
    include_dirs.append(pythondir)
    include_dirs.append(os.path.join(proj_dir, "src", "include"))
    include_dirs.append(os.path.join(proj_dir, "build", "include"))

    # Add ciostream native header path (ciostream_native.h)
    # Search pip-installed location first (Linux/macOS: lib/python*/site-packages,
    # Windows: Lib/site-packages), then fall back to source layout.
    import glob
    _ciostream_found = False
    for _pattern in [
        os.path.join(proj_dir, "packages", "python", "lib", "python*", "site-packages", "ciostream"),
        os.path.join(proj_dir, "packages", "python", "Lib", "site-packages", "ciostream"),
        os.path.join(os.path.dirname(proj_dir), "ciostream", "src", "ciostream"),
        os.path.join(proj_dir, "packages", "ciostream", "src", "ciostream"),
    ]:
        _matches = glob.glob(_pattern)
        if _matches and os.path.isdir(_matches[0]):
            include_dirs.append(_matches[0])
            _ciostream_found = True
            break

    # Add debug_mgr include path (needed for dmgr/IDebugMgr.h in PyParserUtils.h)
    for _pattern in [
        os.path.join(proj_dir, "packages", "python", "lib", "python*", "site-packages", "debug_mgr", "share", "include"),
        os.path.join(proj_dir, "packages", "python", "Lib", "site-packages", "debug_mgr", "share", "include"),
    ]:
        _matches = glob.glob(_pattern)
        if _matches and os.path.isdir(_matches[0]):
            include_dirs.append(_matches[0])
            break

library_dirs = []
libraries = []
extra_link_args = []

ast_ext = Extension(
    "pssparser.ast",
    [
        os.path.join(pythondir, "ast.pyx"),
        os.path.join(pythondir, "PyBaseVisitor.cpp"),
    ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
    language="c++")
ext = Extension(
    "pssparser.core",
    [ os.path.join(pythondir, "core.pyx"),
        os.path.join(pythondir, "PyParserUtils.cpp"),
    ],
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    extra_link_args=extra_link_args,
    language="c++")

extensions=[ast_ext, ext]

setup_requires=['cython', 'ivpm']

if isSrcBuild:
    pass  # pyastbuilder used at cmake time, not setup time

setup_args = dict(
    name="pssparser",
    packages=find_namespace_packages(where='python'),
    package_dir={'' : 'python' },
    package_data={
        'pssparser': [
            "ast.pyi",
            "ast.pxd",
            "ast_decl.pxd",
            "core.pyi",
            "core.pxd",
            "decl.pxd",
        ]
    },
    version=version,
    author="Matthew Ballance",
    author_email="matt.ballance@gmail.com",
    description="Provides a PSS parser and related tools",
    long_description="""
    PSSParser - PSS language parser with ANTLR4 backend
    """,
    ext_modules=extensions,
    entry_points={
        "console_scripts": [
            "pssparser = pssparser.cli.app:main",
        ],
    },
    install_requires=[
        'debug-mgr',
        'ciostream'
    ],
    setup_requires=setup_requires,
)

if isSrcBuild:
    import shutil

    setup_args["ivpm_extdep_pkgs"] = ["debug-mgr", "ciostream"]
    setup_args["ivpm_extdep_data"] = [
        (os.path.join(proj_dir, "build", "pssparser_ast", "ext", 'ast_decl.pxd'),
            os.path.join(proj_dir, "python", "pssparser", 'ast_decl.pxd')),
        (os.path.join(proj_dir, "build", "pssparser_ast", "ext", 'ast.pyi'),
            os.path.join(proj_dir, "python", "pssparser", 'ast.pyi')),
        (os.path.join(proj_dir, "build", "pssparser_ast", "ext", 'ast.pxd'),
            os.path.join(proj_dir, "python", "pssparser", 'ast.pxd')),
        (os.path.join(proj_dir, "build", "pssparser_ast", "ext", 'ast.pyx'),
            os.path.join(proj_dir, "python", 'ast.pyx')),
        (os.path.join(proj_dir, "build", "pssparser_ast", "ext", 'PyBaseVisitor.cpp'),
            os.path.join(proj_dir, "python", 'PyBaseVisitor.cpp')),
        (os.path.join(proj_dir, "build", "pssparser_ast", "ext", 'PyBaseVisitor.h'),
            os.path.join(proj_dir, "python", 'PyBaseVisitor.h')),
    ]

    if platform.system() == "Linux":
        antlr4_rt_lib = None
        for libdir in ("lib", "lib64"):
            if os.path.exists("build/%s/libantlr4-runtime.so" % libdir):
                for f in os.listdir("build/%s" % libdir):
                    if f.startswith("libantlr4-runtime.so."):
                        antlr4_rt_lib = "build/{libdir}/%s" % f
                        break
            if antlr4_rt_lib is not None:
                break

        print("antlr4_rt_lib: %s" % antlr4_rt_lib)
    else:
        antlr4_rt_lib = "build/{libdir}/{libpref}antlr4-runtime{dllext}"

    setup_args["ivpm_extra_data"] = {
        "pssparser": [
            ("build/include", "share"),
            (antlr4_rt_lib, ""),
            ("build/{libdir}/{libpref}ast{dllext}", ""),
            ("build/{libdir}/{libpref}pssparser{dllext}", ""),
            ("python/PyBaseVisitor.h", "share/include"),
            ("python/PyParserUtils.h", "share/include"),
        ]
    }

setup(**setup_args)
