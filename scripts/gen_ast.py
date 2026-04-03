import os
import sys
import platform
import subprocess


def _patch_ast_pyx(path):
    """Replace hardcoded 'libast.so' with platform-specific names and add macOS antlr4 preload."""
    with open(path, 'r') as f:
        content = f.read()

    # Add 'import sys' after 'import os' if not already present
    if 'import sys\n' not in content:
        content = content.replace('import os\n', 'import os\nimport sys\n', 1)

    # Replace hardcoded libname assignment with platform-specific detection
    content = content.replace(
        '            libname = "libast.so"\n',
        '            if sys.platform == \'darwin\':\n'
        '                libname = "libast.dylib"\n'
        '            elif sys.platform == \'win32\':\n'
        '                libname = "ast.dll"\n'
        '            else:\n'
        '                libname = "libast.so"\n'
    )

    # Fix the fallback path (no longer hardcode the .so extension)
    content = content.replace(
        '                core_lib = os.path.join(ext_dir, "libast.so")\n',
        '                core_lib = os.path.join(ext_dir, libname)\n'
    )

    # Add macOS antlr4 preload before ctypes.cdll.LoadLibrary
    content = content.replace(
        '            so = ctypes.cdll.LoadLibrary(core_lib)\n',
        '            if sys.platform == \'darwin\':\n'
        '                import glob as _glob\n'
        '                for _al in _glob.glob(os.path.join(os.path.dirname(core_lib), \'libantlr4-runtime*.dylib\')):\n'
        '                    ctypes.cdll.LoadLibrary(_al)\n'
        '            so = ctypes.cdll.LoadLibrary(core_lib)\n'
    )

    with open(path, 'w') as f:
        f.write(content)


def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    proj_dir = os.path.dirname(scripts_dir)

    if os.path.isdir(os.path.join(proj_dir, "packages")):
        packages_dir = os.path.join(proj_dir, "packages")
    else:
        packages_dir = os.path.dirname(proj_dir)

    print("proj_dir: %s" % str(proj_dir), flush=True)
    print("packages_dir: %s" % str(packages_dir), flush=True)

    sys.path.insert(0, os.path.join(packages_dir, "pyastbuilder", "src"))

    print("PYTHONPATH: %s" % str(sys.path), flush=True)

    env = os.environ.copy()
    ps = ";" if platform.system() == "Windows" else ":"
    env["PYTHONPATH"] = ps.join(sys.path)

    try:
        import astbuilder
    except ImportError as e:
        print("Failed to import astbuilder: %s" % str(e))

    if os.path.exists("pssparser_ast.d"):
        print("Checking timestamps")
        for f in os.listdir(os.path.join(proj_dir, "ast")):
            print("File: %s" % f)

    cmd = [sys.executable, "-m", "astbuilder", "gen-cpp", "-name", "ast"]
    cmd.extend(["-namespace", "pssp::ast", "-astdir", os.path.join(proj_dir, "ast")])
    cmd.extend(["-license", os.path.join(proj_dir, "etc", "copyright.cpp")])

    result = subprocess.run(
        cmd,
        stderr=subprocess.STDOUT,
        stdout=sys.stdout,
        env=env)
    if result.returncode != 0:
        raise Exception("Failed to run gen-cpp")

    cmd = [sys.executable, "-m", "astbuilder", "gen-pyext", "-name", "ast"]
    cmd.extend(["-namespace", "pssp::ast", "-astdir", os.path.join(proj_dir, "ast")])
    cmd.extend(["-package", "pssparser.ast", "-o", "../ext"])

    result = subprocess.run(
        cmd,
        stderr=subprocess.STDOUT,
        stdout=sys.stdout,
        env=env)
    if result.returncode != 0:
        raise Exception("Failed to run gen-pyext")

    # Patch the generated ast.pyx to use platform-specific library names
    # and preload antlr4 on macOS (the generated code hardcodes "libast.so").
    ast_pyx = os.path.abspath(os.path.join("..", "ext", "ast.pyx"))
    if os.path.isfile(ast_pyx):
        _patch_ast_pyx(ast_pyx)

    with open("pssparser_ast.d", "w") as fp:
        fp.write("\n")

if __name__ == "__main__":
    main()
