"""A stand-in for the ``astb`` domain when pyastbuilder's Sphinx support is
not installed.

The AST model reference is rendered from ``ast/*.yaml`` by
``astbuilder.sphinx`` (pyastbuilder with the ``sphinx`` extra). A docs build
without it (a docs job that installs only Sphinx, or a pyastbuilder release
older than that support) still has to succeed, so conf.py loads this instead:
roles render their target as code, and each directive leaves a short note
saying what is missing.
"""
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.domains import Domain

NOTE = ("This part of the AST reference is generated from ast/*.yaml by "
        "pyastbuilder's Sphinx support, which this documentation build did not "
        "have (install pyastbuilder[sphinx]).")


def _role(name, rawtext, text, lineno, inliner, options=None, content=None):
    target = text.split("<")[-1].rstrip(">").strip() if "<" in text else text
    return [nodes.literal(rawtext, target.lstrip("~!"))], []


class _Note(Directive):
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec = {k: directives.unchanged for k in (
        "model", "group", "depth", "max-children", "no-refs", "no-text", "no-diagram",
        "no-projections", "no-appears-in", "no-paths")}
    noted = set()

    def run(self):
        # One note per page is enough.
        doc = self.state.document
        if id(doc) in _Note.noted:
            return []
        _Note.noted.add(id(doc))
        return [nodes.note("", nodes.paragraph(NOTE, NOTE))]


class AstbFallbackDomain(Domain):
    name = "astb"
    label = "AST model (unavailable)"
    roles = {r: _role for r in
             ("class", "struct", "enum", "flags", "type", "field", "enumvalue")}
    directives = {d: _Note for d in (
        "model", "class", "struct", "enum", "flags", "model-map", "inheritance-tree",
        "inheritance-diagram", "containment-diagram", "neighbourhood", "relations-table",
        "projection-table", "legend")}

    def resolve_any_xref(self, *args):
        return []


def setup(app):
    app.add_domain(AstbFallbackDomain)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
