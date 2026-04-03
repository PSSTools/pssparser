import os
import sys
import platform
import subprocess

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

    with open("pssparser_ast.d", "w") as fp:
        fp.write("\n")

if __name__ == "__main__":
    main()
