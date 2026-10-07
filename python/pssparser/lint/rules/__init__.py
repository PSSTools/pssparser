"""Lint rules run by pssparser itself (rather than raised by the C++ linker).

Each module defines rules; ``CHECKERS`` lists the checker classes the bundled
extension registers.  Empty until the lint runner (plan F3) lands.
"""

CHECKERS: list = []
