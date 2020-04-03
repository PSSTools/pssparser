
import os
import sys
import subprocess

def main():
    sys_dir = os.path.dirname(os.path.abspath(__file__))
    pssparser_dir = os.path.dirname(sys_dir)
    
    test_files = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            test_files.append(arg)
    else:
        # Auto-discover tests
        if not os.path.isdir(os.path.join(sys_dir, "portable-stimulus")):
            print("Error: Expecting portable-stimulus to be checked out in the sys directory")
            sys.exit(1)

        spec_examples = os.path.join(sys_dir, "portable-stimulus", "spec_examples")
    
        for f in os.listdir(spec_examples):
            if f.endswith(".pss") and f[0] in ("0", "1", "2", "3"):
                test_files.append(os.path.join(spec_examples, f))
            
    test_files.sort()
            
    # TODO: determine how to set path and which python to run
    os.environ["PYTHONPATH"] = os.path.join(pssparser_dir, "src")
    
    if os.path.isdir(os.path.join(pssparser_dir, "packages")):
        python_dir = os.path.join(pssparser_dir, "packages", "python")
        if os.path.isdir(os.path.join(python_dir, "Scripts")):
            python = os.path.join(python_dir, "Scripts", "python")
        else:
            python = os.path.join(python_dir, "bin", "python")
    else:
        python = "python3"
        
    if len(test_files) == 0:
        print("Error: no tests found")
        sys.exit(1)

    # Now, run tests
    n_passed = 0
    n_failed = 0
    for tf in test_files:
        testname = os.path.basename(tf)
        print("Running Test: " + testname)
        sys.stdout.flush()
        status = subprocess.call([
            python,
            "-m", "pssparser",
            tf])
        if status == 0:
            print("PASS: " + testname)
            n_passed += 1
        else:
            print("FAIL: " + testname)
            n_failed += 1
            
    print("Passed=%d Failed=%d Total=%0d" % (n_passed, n_failed, n_passed+n_failed))

    if n_failed == 0:
        sys.exit(0)
    else:
        sys.exit(1)
        

if __name__ == "__main__":
    main()

