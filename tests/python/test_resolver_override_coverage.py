"""Every TaskResolveRefs override walks every child that can hold a reference
(symbol-resolution plan WS3.4, INV-3).

``TaskResolveRefs`` overrides many generated visitors.  An override that does
not chain to ``VisitorBase::visitX`` has to visit each child itself, and the
ones that forgot a field are how parameter defaults, ``repeat`` counts, slice
bounds, traversal subscripts and initializer values all went unresolved
(report F §3.5).  This lint reads the schema (``ast/*.yaml``) and the override
bodies, and fails when an override neither chains nor reads a child field.

What counts as a child: an owned node field (``UP<X>`` or ``list<UP<X>>``) that
is visited by the generated walk.  Bare ``ExprId`` fields are left out -- they
are declaration names or unbindable references, which WS3.1/3.2 classify -- as
are ``AssocData`` and annotations (unknown annotations are disregarded, §7.13;
``checkScopeAnnotations`` handles them).

An override "reads" a field when its body -- or a member function it hands
the node to, e.g. ``resolveExprRefPathContext(i)`` -- calls the field's getter.
A deliberate skip goes in ALLOWED with the reason.  Stale entries fail too, so
the list only ever describes the code as it is.

Limit: only an override's *direct* children are checked.  It would have caught
the ``repeat`` count, the slice and the initializers, but not a parameter's
``dflt`` or a path element's subscripts, which sit one level down; T-miss
(scripts/refcov_slots.py) is what covers those.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from refcov import load_schema  # noqa: E402

SKIP_TYPES = {"ExprId", "AssocData", "Annotation"}

#: The body fields that src/include/pssp/impl/ActivityScopes.h's ``bodies()``
#: reads. An override that hands its node to ``ActivityScopes::bodies`` walks
#: them without naming their getters. Keep in step with that function.
ACTIVITY_BODY_FIELDS = {
    "ActivityRepeatCount.body", "ActivityRepeatWhile.body",
    "ActivityForeach.body", "ActivityReplicate.body",
    "ActivityAtomicBlock.body", "ActivityIfElse.true_s",
    "ActivityIfElse.false_s", "ActivitySelect.branches",
    "ActivityMatch.choices", "MonitorActivityEventually.body",
}

#: The same for src/include/pssp/impl/ProceduralScopes.h's ``bodies()`` (4.1b).
#: If-clause and match-choice bodies sit one level down, so only the direct
#: fields are listed.
PROCEDURAL_BODY_FIELDS = {
    "ProceduralStmtIfElse.if_then", "ProceduralStmtIfElse.else_then",
    "ProceduralStmtMatch.choices", "ProceduralStmtBody.body",
}

#: Compound activity statements: SymbolScopes (WS4.1) that never carry imports.
ACTIVITY_SCOPES = (
    "ActivityAtomicBlock", "ActivityForeach", "ActivityIfElse",
    "ActivityMatch", "ActivityRepeatCount", "ActivityRepeatWhile",
    "ActivityReplicate", "ActivitySelect", "MonitorActivityEventually",
)

ALLOWED = {
    # Imports exist only on package, component and type scopes; the other
    # scope kinds inherit the field but never populate it.
    "visitExecScope:SymbolScope.imports": "never populated on an exec scope",
    "visitProceduralStmtForeach:SymbolScope.imports": "never populated on a loop",
    "visitProceduralStmtRepeat:SymbolScope.imports": "never populated on a loop",
    "visitTemplateAssign:SymbolScope.imports": "never populated on a template scope",
    "visitTemplateBlock:SymbolScope.imports": "never populated on a template scope",
    "visitTemplateString:SymbolScope.imports": "never populated on a template scope",
    "visitSymbolExtendScope:SymbolScope.imports":
        "every import is resolved before this pass (TaskResolveImports::resolveAll)",
    "visitSymbolScope:SymbolScope.imports":
        "every import is resolved before this pass (TaskResolveImports::resolveAll)",
    "visitSymbolFunctionScope:SymbolScope.imports": "never populated on a function scope",
    # Loop scopes: `children` holds the loop variable's declaration; the body
    # is walked through getBody().
    "visitProceduralStmtForeach:SymbolChildrenScope.children":
        "the loop variables' declarations, typed by typeLoopIterator; the body is getBody()",
    "visitProceduralStmtRepeat:SymbolChildrenScope.children":
        "the loop variable's declaration; the body is getBody()",
    "visitTemplateAssign:SymbolChildrenScope.children":
        "the declared template local; the value is walked explicitly",
    # Extensions are applied, and their targets resolved, by
    # TaskApplyTypeExtensions before this pass; the merged members are walked
    # in the extended type.
    "visitExtendEnum:ExtendEnum.target": "resolved by TaskApplyTypeExtensions",
    "visitExtendEnum:ExtendEnum.items": "merged into the enum, walked there",
    "visitExtendType:ExtendType.target": "resolved by TaskApplyTypeExtensions",
    "visitExtendType:ExtendType.imports":
        "every import is resolved before this pass (TaskResolveImports::resolveAll)",
    "visitExtendType:Scope.children": "merged into the type, walked there",
    # Deliberately not resolved yet: each needs its own rules, and the
    # ordinary lookup would report legal code (see the overrides' comments).
    "visitActivityBindStmt:ActivityBindStmt.lhs": "WS4.5 (U2)",
    "visitActivityBindStmt:ActivityBindStmt.rhs": "WS4.5 (U2)",
    "visitActivitySchedulingConstraint:ActivitySchedulingConstraint.targets":
        "label paths: WS4.3 (F-N11)",
    "visitComponentBind:ComponentBind.pool_path": "component paths: WS4.5 (U2)",
    "visitInstanceOverride:InstanceOverride.target": "instance paths: U5",
    # `comp` is typed by TaskLinkActionCompRefFields (WS5.3 for its gaps).
    "visitFieldCompRef:FieldCompRef.type": "typed by TaskLinkActionCompRefFields",
    # An import spec carries a platform and a language, no names.
    "visitSymbolFunctionScope:SymbolFunctionScope.import_specs": "no references",
    # The symbol-tree mirrors of a template's parameters and specializations:
    # the parameters are walked through the type's getParams(), and each
    # specialization is resolved when it is created.
    "visitSymbolTypeScope:SymbolTypeScope.plist": "walked through getParams()",
    "visitSymbolTypeScope:SymbolTypeScope.spec_types": "resolved when created",
}
ALLOWED.update({
    "visit%s:SymbolScope.imports" % c: "never populated on an activity scope"
    for c in ACTIVITY_SCOPES})


def _child_fields(classes, cls):
    out = []
    while cls in classes:
        _, sup, fields = classes[cls]
        for fn, t, vis in fields:
            m = re.match(r"^(?:list<)?\s*UP<\s*(\w+)\s*>\s*>?$", (t or "").strip())
            if m and m.group(1) in classes and vis is not False \
                    and m.group(1) not in SKIP_TYPES:
                out.append((cls, fn))
        cls = sup
    return out


def _supers(classes, cls):
    out = []
    while cls in classes:
        out.append(cls)
        cls = classes[cls][1]
    return out


def _bodies(src, qual):
    """{method name: (param name, param class, body)} for methods whose last
    parameter is a node (a visitor has only that one)."""
    out = {}
    pat = re.compile(
        r"void\s+%s(\w+)\s*\((?:[^();{]*,)?\s*ast::I(\w+)\s*\*\s*(\w+)\s*\)[^;{]*\{"
        % qual)
    for m in pat.finditer(src):
        start, depth = m.end(), 1
        i = start
        while depth and i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
            i += 1
        out.setdefault(m.group(1), (m.group(3), m.group(2), src[start:i]))
    return out


def _expand(methods, name, seen=None):
    """A body plus the bodies of member functions it hands its node to, as
    the last argument."""
    seen = seen or set()
    seen.add(name)
    var, _, body = methods[name]
    text = body
    for m in re.finditer(r"\b(\w+)\s*\((?:[^();]*,)?\s*%s\s*\)" % var, body):
        callee = m.group(1)
        if callee in methods and callee not in seen and not callee.startswith("visit"):
            text += _expand(methods, callee, seen).replace(methods[callee][0], var)
    return text


def _unvisited():
    classes = load_schema()
    cpp = (ROOT / "src" / "TaskResolveRefs.cpp").read_text()
    hdr = (ROOT / "src" / "TaskResolveRefs.h").read_text()
    methods = _bodies(cpp, "TaskResolveRefs::")
    for k, v in _bodies(hdr, "").items():
        methods.setdefault(k, v)

    missing = set()
    for name in sorted(methods):
        if not name.startswith("visit"):
            continue
        cls = name[len("visit"):]
        if cls not in classes or methods[name][1] != cls:
            continue
        var = methods[name][0]
        body = _expand(methods, name)
        if re.search(r"VisitorBase::visit%s\s*\(" % cls, body):
            continue
        covered = set()
        for m in re.finditer(r"\bvisit(\w+)\s*\(\s*%s\s*\)" % var, body):
            covered.update(_supers(classes, m.group(1)))
        for m in re.finditer(r"VisitorBase::visit(\w+)\s*\(", body):
            covered.update(_supers(classes, m.group(1)))
        via_bodies = "ActivityScopes::bodies(" in body
        via_proc_bodies = "ProceduralScopes::bodies(" in body
        for owner, fn in _child_fields(classes, cls):
            if owner in covered:
                continue
            if via_bodies and "%s.%s" % (owner, fn) in ACTIVITY_BODY_FIELDS:
                continue
            if via_proc_bodies and "%s.%s" % (owner, fn) in PROCEDURAL_BODY_FIELDS:
                continue
            getter = "get" + fn[0].upper() + fn[1:]
            if not re.search(r"\b%s\s*\(" % getter, body):
                missing.add("%s:%s.%s" % (name, owner, fn))
    return missing


def test_every_override_walks_its_reference_children():
    missing = _unvisited()
    new = sorted(missing - set(ALLOWED))
    assert not new, (
        "TaskResolveRefs overrides that neither chain to VisitorBase nor read "
        "these child fields -- visit them, or add them to ALLOWED with the "
        "reason:\n  " + "\n  ".join(new))


def test_allowed_list_is_not_stale():
    stale = sorted(set(ALLOWED) - _unvisited())
    assert not stale, "ALLOWED entries that are now visited -- remove them:\n  " \
        + "\n  ".join(stale)
