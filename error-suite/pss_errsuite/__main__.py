"""`python3 -m pss_errsuite …`

The README's headline invocation, and the one that works with no install
step -- which is the point of a stdlib-only suite a third party is meant to
be able to run in two commands.
"""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
