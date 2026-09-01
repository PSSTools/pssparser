"""Grammar profiling: measure where PSSParser.g4 makes ALL(*) work hard.

See ``docs/design/grammar-profiling-harness.md``.  A private submodule -- it is
not re-exported from ``pssparser`` -- but it lives in the package rather than
in ``tests/`` because it is useful outside the suite: bisecting a grammar
change, or profiling a model that is not in the corpus.

Entry point: ``scripts/profile_grammar.py``.
"""
from .model import CorpusProfile, DecisionSample, Event, FileProfile, SCHEMA_VERSION

__all__ = [
    "CorpusProfile",
    "DecisionSample",
    "Event",
    "FileProfile",
    "SCHEMA_VERSION",
]
