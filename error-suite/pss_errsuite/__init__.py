"""pss-errsuite: a tool-neutral PSS error-reporting test suite.

Runs a corpus of deliberately-broken (and deliberately-valid) PSS against any
tool that can be described in ~20 lines of TOML, and records what the tool said
-- with no pass/fail opinion baked in.  See docs/design/error-suite-design.md.

Stdlib only, by design: the suite has to be runnable by someone who has another
vendor's tool and a stock interpreter.
"""

__version__ = "0.1.0"
