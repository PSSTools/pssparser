"""Adapters: the only part of the harness that knows how a tool is invoked."""
from __future__ import annotations

from .base import (Capabilities, CaseOpts, Diagnostic, Related, ToolAdapter,
                   ToolResult)

__all__ = ["Capabilities", "CaseOpts", "Diagnostic", "Related", "ToolAdapter",
           "ToolResult", "make_adapter"]


def make_adapter(desc):
    """Build the adapter a descriptor asks for."""
    if desc.adapter == "pssparser-inprocess":
        from .inprocess_pssparser import InProcessPssparserAdapter
        return InProcessPssparserAdapter(desc)
    from .subprocess_cli import SubprocessAdapter
    return SubprocessAdapter(desc)
