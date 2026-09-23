/*
 * TaskResolveRefs.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include <set>
#include "dmgr/impl/DebugMacros.h"
#include "CoreLibraryLookup.h"
#include "TaskCheckCallArgs.h"
#include "TaskExprTypeCat.h"
#include "TaskCompareTypeRefs.h"
#include "TaskFindPathElem.h"
#include "TaskLinkActionCompRefFields.h"
#include "TaskResolveImports.h"
#include "TaskResolveRef.h"
#include "TaskResolveRootRef.h"
#include "pssp/ast/ITypeScope.h"
#include "pssp/ast/IProceduralStmtSuper.h"
#include "pssp/ast/IActivitySuper.h"
#include "TaskResolveRefs.h"
#include "TaskTemplateCheck.h"
#include "pssp/ast/IExprTemplateString.h"
#include "pssp/ast/IGenericConstraintDeclBool.h"
#include "pssp/ast/IGenericConstraintDeclValue.h"
#include "pssp/ast/IGenericConstraintParam.h"
#include "TaskSpecializeParameterizedRef.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "pssp/impl/ActivityScopes.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/IActionHandleField.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/IActivityActionHandleTraversal.h"
#include "pssp/ast/IActivityActionTypeTraversal.h"
#include "pssp/ast/IActivityLabeledScope.h"
#include "pssp/ast/IActivityLabeledStmt.h"
#include "pssp/ast/IConstraintBlock.h"
#include "pssp/ast/IMonitor.h"
#include "pssp/impl/TaskGetElemSymbolScope.h"
#include "pssp/impl/TaskGetSubscriptSymbolScope.h"
#include "pssp/impl/TaskGetCollectionElemType.h"
#include "pssp/impl/BuiltinCollectionUtil.h"
#include "pssp/impl/InternalError.h"
#include "pssp/impl/TaskIsPyRef.h"
#include "pssp/ast/IExprAggrList.h"
#include "pssp/ast/IExprAggrStruct.h"
#include "pssp/ast/IExprAggrStructElem.h"
#include "pssp/ast/IExprString.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IStruct.h"
#include "pssp/ast/ISymbolTypeScope.h"
#include "pssp/ast/ITemplateGenericTypeParamDecl.h"
#include "pssp/ast/ITemplateParamDeclList.h"
#include "pssp/ast/IDataTypeUserDefined.h"
#include "pssp/ast/IDataTypeEnum.h"
#include "pssp/ast/IExprBitSlice.h"
#include "pssp/ast/IFunctionImportType.h"
#include "pssp/ast/IEnumDecl.h"
#include "pssp/ast/ISymbolDeclaration.h"
#include "pssp/ast/IComponentBind.h"
#include "pssp/ast/IComponentBindTarget.h"
#include "pssp/ast/IInstanceOverride.h"
#include "pssp/ast/IExportFunction.h"
#include "pssp/ast/IExprRefName.h"
#include "pssp/ast/IActivitySymbolCall.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IExprBool.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "pssp/IValInt.h"
#include "pssp/ast/IActionFieldInitializer.h"
#include "pssp/ast/IExprDomainOpenRangeList.h"
#include "pssp/ast/IExprMemberCall.h"
#include "pssp/ast/IExprTemplateString.h"
#include "pssp/ast/IExprAggrLiteral.h"
#include "pssp/ast/IDataTypeString.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/ISymbolEnumScope.h"
#include "pssp/ast/ITypeIdentifier.h"

#include "pssp/impl/ProceduralScopes.h"
#include <algorithm>

namespace pssp {

/**
 * Methods available on the built-in types, which have no declaration in the
 * standard library and so cannot be resolved through the symbol table.
 *
 * Kept in one place: these lists were previously duplicated at each use site,
 * and drifted -- `sum` was present in the LRM but missing from both copies,
 * which is why `a.sum()` failed while `a.size()` worked.
 */
namespace {

//: LRM 7.6.3 -- string methods
const std::set<std::string> &stringMethods() {
    static const std::set<std::string> s = {
        "size", "len",
        "find", "rfind", "find_last", "find_all",
        "substr",
        "lower", "upper", "to_lower", "to_upper",
        "starts_with", "ends_with", "trim",
        "split", "chars"
    };
    return s;
}

//: LRM 7.9.2.2 (array), 7.9.3.2 (list), 7.9.4.2 (set), 7.9.5.2 (map)
const std::set<std::string> &collectionMethods() {
    static const std::set<std::string> s = {
        "size",
        "push_back", "pop_back", "push_front", "pop_front",
        "insert", "delete", "clear",
        "contains", "find",
        "sort", "rsort", "shuffle", "reverse", "unique",
        "join", "str_from_chars",
        "sum", "to_list", "to_set",
        "keys", "values",
        "front", "back",
        "set", "get"
    };
    return s;
}

//: The union, for the "is this a method on a built-in at all?" test.
const std::set<std::string> &builtinMethods() {
    static const std::set<std::string> s = [] {
        std::set<std::string> merged = stringMethods();
        merged.insert(collectionMethods().begin(), collectionMethods().end());
        return merged;
    }();
    return s;
}

}


static int editDistance_rr(const std::string &a, const std::string &b) {
    int m = a.size(), n = b.size();
    std::vector<std::vector<int>> dp(m+1, std::vector<int>(n+1, 0));
    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            int cost = (a[i-1] != b[j-1]) ? 1 : 0;
            dp[i][j] = std::min({dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost});
        }
    }
    return dp[m][n];
}

/**
 * The `string` pseudo-type built by `BuiltinsFactory`, or null.
 *
 * A string variable has no type *reference* to follow -- `IDataTypeString` names
 * nothing -- so a method call on one cannot reach its methods the way a call on
 * a user-defined type does.  Looking the pseudo-type up by name here is what
 * bridges that gap, and is what lets string methods be checked against real
 * signatures rather than against a list of names (P3-X6d).
 */
static ast::ISymbolScope *builtinStringScope_rr(ast::ISymbolScope *root) {
    if (!root) return 0;
    std::unordered_map<std::string, int32_t>::const_iterator it =
        root->getSymtab().find("string");
    if (it == root->getSymtab().end()) return 0;
    return dynamic_cast<ast::ISymbolScope *>(
        root->getChildren().at(it->second).get());
}

static std::string findCloseMatch_rr(
        const std::string &name,
        ast::ISymbolScope *scope,
        int maxDist = 2) {
    std::string best;
    int bestDist = maxDist + 1;
    if (!scope) return best;
    for (auto &entry : scope->getSymtab()) {
        int d = editDistance_rr(name, entry.first);
        if (d > 0 && d < bestDist) {
            bestDist = d;
            best = entry.first;
        }
    }
    for (auto &child : scope->getChildren()) {
        ast::ISymbolEnumScope *enum_s =
            dynamic_cast<ast::ISymbolEnumScope *>(child.get());
        if (enum_s) {
            for (auto &entry : enum_s->getSymtab()) {
                int d = editDistance_rr(name, entry.first);
                if (d > 0 && d < bestDist) {
                    bestDist = d;
                    best = entry.first;
                }
            }
        }
    }
    return best;
}

/**
 * True if any subscript on `elem` is a slice (`[a..b]`) rather than a plain
 * index (`[a]`).
 *
 * The distinction changes the type of the path so far: an index selects one
 * element, while a slice selects a sub-collection. So `arr[1].f` names a field
 * of an element, but `arr[1..3].f` names a field of a *list*, which does not
 * exist. Both spellings reach the resolver as entries in the same subscript
 * list, so without this the two are indistinguishable and a slice is silently
 * resolved as though it were an index.
 */
static bool hasSliceSubscript_rr(ast::IExprMemberPathElem *elem) {
    for (std::vector<ast::IExprUP>::const_iterator
        it=elem->getSubscript().begin();
        it!=elem->getSubscript().end(); it++) {
        if (dynamic_cast<ast::IExprSliceRange *>(it->get())) {
            return true;
        }
    }
    return false;
}




TaskResolveRefs::TaskResolveRefs(ResolveContext *ctxt) : TaskResolveBase(ctxt) {
    DEBUG_INIT("TaskResolveRefs", ctxt->getDebugMgr());
}

TaskResolveRefs::~TaskResolveRefs() {

}

void TaskResolveRefs::resolve(ast::ISymbolScope *root) {
    DEBUG_ENTER("resolve (SymbolScope root) %d %p (%s)", 
        root->getSymtab().size(), 
        root,
        root->getName().c_str());
//    m_root = root;
    m_ctxt->pushSymtab(m_ctxt->getFactory()->mkAstSymbolTableIterator(root));

    // First, ensure all actions have their 'comp' refs updated
    // Should this be done at root level?
    TaskLinkActionCompRefFields(m_ctxt->getFactory()).link(root);

    // Phases:
    // - 

    if (root->getImports()) {
        DEBUG_ENTER("  Resolve Imports");
        TaskResolveImports(m_ctxt).resolve(root);
        DEBUG_LEAVE("  Resolve Imports");
    }

    DEBUG("resolve ==> process children");
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=root->getChildren().begin();
        it!=root->getChildren().end(); it++) {
        it->get()->accept(this);
    }
    DEBUG("resolve <== process children");

    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve");
}

namespace {

/** Every Scope in a unit that carries a CompileCond, with the conditions. */
class CompileCondFinder : public ast::VisitorBase {
public:
    std::vector<ast::IScope *>      scopes;

    virtual void visitScope(ast::IScope *i) override {
        if (i->getCompile_conds().size()) {
            scopes.push_back(i);
        }
        VisitorBase::visitScope(i);
    }
};

/** The `compile has(...)` operands under an expression (not walked by the
 *  generated visitor, which is the point of them). */
class CompileHasFinder : public ast::VisitorBase {
public:
    std::vector<ast::IExprRefPath *> refs;

    virtual void visitExprCompileHas(ast::IExprCompileHas *i) override {
        if (i->getRef()) {
            refs.push_back(i->getRef());
        }
        VisitorBase::visitExprCompileHas(i);
    }
};

/** The symbol scope each AST scope (type, package) stands under. */
class SymbolScopeMap : public ast::VisitorBase {
public:
    std::map<ast::IScopeChild *, ast::ISymbolScope *>   m;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override {
        if (i->getTarget()) {
            m.emplace(i->getTarget(), i);
        }
        VisitorBase::visitSymbolScope(i);
    }

    // The symbol tree only, not the AST it points into.
    virtual void visitScope(ast::IScope *i) override { }
};

}

void TaskResolveRefs::resolveCompileConds(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("resolveCompileConds");
    SymbolScopeMap sym;
    for (auto it=root->getChildren().begin(); it!=root->getChildren().end(); it++) {
        (*it)->accept(&sym);
    }

    m_ctxt->pushQuiet();
    for (auto u_it=root->getUnits().begin(); u_it!=root->getUnits().end(); u_it++) {
        CompileCondFinder finder;
        (*u_it)->accept(&finder);

        for (auto s_it=finder.scopes.begin(); s_it!=finder.scopes.end(); s_it++) {
            ast::IScope *scope = *s_it;

            // The symbol scope to resolve in. A package's symbol scope has
            // no AST target (it stands for every block of that name), and an
            // `extend` block resolves in the type it extends.
            ast::ISymbolScope *sym_s = 0;
            auto m_it = sym.m.find(scope);
            if (m_it != sym.m.end()) {
                sym_s = m_it->second;
            } else if (ast::IPackageScope *pkg = dynamic_cast<ast::IPackageScope *>(scope)) {
                ast::ISymbolScope *s = root;
                for (auto id_it=pkg->getId().begin(); s && id_it!=pkg->getId().end(); id_it++) {
                    auto st_it = s->getSymtab().find((*id_it)->getId());
                    s = (st_it != s->getSymtab().end())
                        ? dynamic_cast<ast::ISymbolScope *>(s->getChildren().at(st_it->second).get())
                        : 0;
                }
                sym_s = s;
            } else if (ast::IExtendType *ext = dynamic_cast<ast::IExtendType *>(scope)) {
                if (ext->getTarget() && ext->getTarget()->getTarget()) {
                    sym_s = dynamic_cast<ast::ISymbolScope *>(
                        m_ctxt->resolveSymbolPathRef(ext->getTarget()->getTarget()));
                }
            }
            if (!sym_s) {
                sym_s = root;
            }

            m_ctxt->pushSymtab(TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(), root).mkIterator(
                    m_ctxt->getFactory()->mkAstSymbolTableIterator(root), sym_s));
            for (auto c_it=scope->getCompile_conds().begin();
                    c_it!=scope->getCompile_conds().end(); c_it++) {
                ast::IExpr *cond = (*c_it)->getCond();
                if (!cond) {
                    continue;
                }
                cond->accept(m_this);
                CompileHasFinder has;
                cond->accept(&has);
                for (auto h_it=has.refs.begin(); h_it!=has.refs.end(); h_it++) {
                    (*h_it)->accept(m_this);
                }
            }
            m_ctxt->popSymtab();
        }
    }
    m_ctxt->popQuiet();
    DEBUG_LEAVE("resolveCompileConds");
}

/**
 * True if `c`, a child of type scope `s`, is only an alias for a labeled
 * activity statement: registerActivityLabels makes each label a symtab entry of
 * the action so that a path rooted at it resolves, and the statement itself is
 * walked where it is written, in its block. Walked again from here, it was
 * resolved with the action's scope on top instead of its block's, and a
 * traversal target found in the block got a path that skipped it.
 */
static bool isActivityLabelAlias(ast::ISymbolScope *s, ast::IScopeChild *c) {
    return dynamic_cast<ast::ISymbolTypeScope *>(s)
        && (dynamic_cast<ast::IActivityLabeledStmt *>(c)
            || dynamic_cast<ast::IActivityLabeledScope *>(c));
}

void TaskResolveRefs::resolve(ast::ISymbolTypeScope *scope) {
    // Resolving a specialization's body can specialize again; see
    // TaskGetSpecializedTemplateType for the user-facing depth limit.
    DepthGuard guard(m_ctxt->depth(), "TaskResolveRefs::resolve (type scope)");
    DEBUG_ENTER("resolve (iterator, scope) %s", scope->getName().c_str());

    if (scope->getPlist()) {
        DEBUG_ENTER("Resolving names in plist");
        scope->getPlist()->accept(m_this);
        DEBUG_LEAVE("Resolving names in plist");
    }

    // Create an iterator based on the type-scope itself
    ISymbolTableIterator *type_it = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(),
        m_ctxt->root()).mkIterator(
            m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
            scope);
    // Remove the type itself, since this will be added 
    // during resolution
    type_it->popScope();

    // Is this required here?
    DEBUG("Pushing symbol iterator for body");
    m_ctxt->pushSymtab(type_it);

    ast::SymbolRefPathElemKind kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;

    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(scope->getTarget());
    if (i_ts->getParams() && i_ts->getParams()->getSpecialized()) {
            kind = ast::SymbolRefPathElemKind::ElemKind_TypeSpec;
            DEBUG("Processing specialization depth=%d", m_ctxt->specializationDepth());

            // TODO: need a way to detect that we have a superseding 
            // scope stack, so we don't redo it

            // Create a symbol-table iterator that:
            // - starts with m_root
            // - is preloaded with the scopes of the target type

            // if (m_ctxt->specializationDepth() == 1) {
            //     DEBUG("Updating resolution stack to use local scope");
            //     m_ctxt->pushSymtab(TaskResolveSymbolPathRef(
            //         m_ctxt->getDebugMgr(), m_ctxt->root()).mkIterator(
            //             m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
            //             i));
            // } else {
            //     DEBUG("Retaining existing resolution stack");
            // }
            // // TODO: need to resolve refs in the parameter list
            // // relative to the containing type
            // // Ensure parameter references are resolved
            // DEBUG_ENTER("Resolve refs in parameter decl list");
            // i_ts->getParams()->accept(m_this);
            // DEBUG_LEAVE("Resolve refs in parameter decl list");
            // if (m_ctxt->specializationDepth() == 1) {
            //     m_ctxt->popSymtab();
            // }
        }

    m_ctxt->symtab()->pushScope(scope, kind);

    // The super type is resolved *after* the type's own scope is pushed, not
    // before. A generic may inherit from one of its own parameters
    // (`struct M<type T> : T`), and the parameter is only in scope once the
    // type is. Resolving first meant `T` was looked up in the enclosing scope,
    // where it means nothing -- which is why a generic like that could be
    // specialized directly, where a different path pushes the scope first, but
    // not from inside another generic's body, which comes through here.
    ast::ITypeScope *target_s = dynamic_cast<ast::ITypeScope *>(scope->getTarget());
    if (target_s->getSuper_t()) {
        DEBUG_ENTER("Resolve super type");
        target_s->getSuper_t()->accept(m_this);
        DEBUG_LEAVE("Resolve super type");
    }

    TaskLinkActionCompRefFields(m_ctxt->getFactory()).link(scope);

    // Check on children
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=scope->getChildren().begin();
        it!=scope->getChildren().end(); it++) {
        if (!isActivityLabelAlias(scope, it->get())) {
            visitMergedScopeChild(it->get());
        }
    }

    m_ctxt->symtab()->popScope();

    DEBUG("Removing symbol iterator for body");
    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve (iterator, scope)");
}

/**
 * True if `s` is an action or monitor type: something a traversal can run,
 * and whose members a `with` block or an initializer list names.
 */
static bool isTraversableType(ast::ISymbolScope *s) {
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(s);
    ast::IScopeChild *t = ts ? ts->getTarget() : 0;
    return dynamic_cast<ast::IAction *>(t) || dynamic_cast<ast::IMonitor *>(t);
}

/**
 * The action (or monitor) type a handle traversal runs, given what its target
 * bound to (4.2, U7/K6). Null when there is no type to resolve a `with` block
 * or an initializer list in: the target is not a handle, or is a whole array
 * of them, or its type is unknown.
 *
 * With `report`, a target that cannot be traversed at all is diagnosed here
 * (11.3.1: "identifier names a unique action handle or variable"). What can be:
 *   - a handle of action or monitor type, however it was declared -- an action
 *     field, an activity-local handle, a symbol parameter, a foreach iterator
 *     over handles, or the label of an earlier traversal (11.3.1.1 c, C-N4);
 *     an element or sub-array of a handle array, or the whole array;
 *   - a data field with the `action` modifier (11.3.1, Ex. 173), which is
 *     randomized with no execution;
 *   - a generic constraint (13.4.11), a `dynamic` one (deprecated, 13.1.1),
 *     or a symbol with no parameters (Ex. 120).
 * A fixed constraint cannot be: it always holds (decision Q1).
 *
 * A declaration whose type did not resolve is left alone -- that was reported
 * where the type is written -- and so is one whose type is a template
 * parameter, which has no scope until the generic is specialized.
 */
ast::ISymbolScope *TaskResolveRefs::traversedType(
        ast::IScopeChild            *decl,
        ast::IExprId                *id,
        uint32_t                    n_sub,
        bool                        report) {
    const std::string &name = id->getId();
    const ast::Location &loc = id->getLocation();

    // Tested first: a generic constraint is a ConstraintBlock too.
    if (dynamic_cast<ast::IGenericConstraintDeclBool *>(decl)
            || dynamic_cast<ast::IGenericConstraintDeclValue *>(decl)
            || dynamic_cast<ast::ISymbolDeclaration *>(decl)) {
        return 0;
    }
    if (ast::IConstraintBlock *cb = dynamic_cast<ast::IConstraintBlock *>(decl)) {
        if (!report) {
        } else if (cb->getIs_dynamic()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Warn,
                loc,
                "traversal of dynamic constraint '%s' is deprecated (13.1.1); "
                "declare it as a generic constraint, 'constraint %s() { ... }'",
                name.c_str(), name.c_str());
        } else {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                loc,
                "'%s' is a fixed constraint, which always holds and cannot be "
                "traversed; declare it as a generic constraint, "
                "'constraint %s() { ... }', to apply it here",
                name.c_str(), name.c_str());
        }
        return 0;
    }

    // `T: do A; ... T;` -- a traversal's label is a handle of the traversed
    // type; `T: a;` is `a` (C-N4).
    if (ast::IActivityActionTypeTraversal *tt =
            dynamic_cast<ast::IActivityActionTypeTraversal *>(decl)) {
        ast::ITypeIdentifier *tid = tt->getTarget() ? tt->getTarget()->getType_id() : 0;
        ast::IScopeChild *c = (tid && tid->getTarget())
            ? m_ctxt->resolveSymbolPathRef(tid->getTarget()) : 0;
        return dynamic_cast<ast::ISymbolScope *>(c);
    }
    if (ast::IActivityActionHandleTraversal *ht =
            dynamic_cast<ast::IActivityActionHandleTraversal *>(decl)) {
        ast::IExprMemberPathElem *leaf = (ht->getTarget() && ht->getTarget()->getTarget())
            ? ht->getTarget()->getHier_id()->getElems().back().get() : 0;
        ast::IScopeChild *c = leaf ? leaf->getId()->getDecl() : 0;
        return (c && c != decl)
            ? traversedType(c, leaf->getId(), leaf->getSubscript().size(), false) : 0;
    }

    ast::IField *field = dynamic_cast<ast::IField *>(decl);
    ast::IActionHandleField *handle = dynamic_cast<ast::IActionHandleField *>(decl);
    ast::IFunctionParamDecl *sym_param = dynamic_cast<ast::IFunctionParamDecl *>(decl);
    ast::IProceduralStmtDataDeclaration *loop_var =
        dynamic_cast<ast::IProceduralStmtDataDeclaration *>(decl);
    ast::IDataType *type = field ? field->getType()
        : handle ? handle->getType()
        : sym_param ? sym_param->getType()
        : loop_var ? loop_var->getDatatype() : 0;
    bool is_action_data = field
        && (field->getAttr() & ast::FieldAttr::Action) != ast::FieldAttr::NoFlags;

    if (!type) {
        if (report) {
            if (dynamic_cast<ast::ISymbolTypeScope *>(decl)) {
                m_ctxt->addMarker(
                    MarkerSeverityE::Error,
                    loc,
                    "'%s' is a type, not an action handle; traverse it by type "
                    "with 'do %s'",
                    name.c_str(), name.c_str());
            } else if (dynamic_cast<ast::IActivityLabeledStmt *>(decl)
                    || dynamic_cast<ast::IActivityLabeledScope *>(decl)) {
                m_ctxt->addMarker(
                    MarkerSeverityE::Error,
                    loc,
                    "'%s' is an activity label, not an action handle, and "
                    "cannot be traversed",
                    name.c_str());
            } else {
                m_ctxt->addMarker(
                    MarkerSeverityE::Error,
                    loc,
                    "'%s' is not an action handle, and cannot be traversed; "
                    "only a handle, or a data field declared with the 'action' "
                    "modifier, can be",
                    name.c_str());
            }
        }
        return 0;
    }

    ast::IDataTypeUserDefined *udt = dynamic_cast<ast::IDataTypeUserDefined *>(type);
    if (udt && (!udt->getType_id() || !udt->getType_id()->getTarget())) {
        // Unknown type: already reported at the declaration.
        return 0;
    }
    ast::IScopeChild *type_c = udt
        ? m_ctxt->resolveSymbolPathRef(udt->getType_id()->getTarget()) : 0;
    ast::ISymbolScope *type_s = dynamic_cast<ast::ISymbolScope *>(type_c);

    if (udt && !type_s) {
        // A template parameter, or something else with no scope yet.
        return 0;
    }

    // `a_arr[1] with {...}` constrains an *element*, so the with-block is
    // resolved in the element type.
    ast::ISymbolScope *elem_s = type_s;
    if (type_s && n_sub) {
        elem_s = TaskGetSubscriptSymbolScope(
            m_ctxt->getDebugMgr(), m_ctxt->root(), n_sub).resolve(decl);
    }

    if (elem_s && builtinCollectionKind(elem_s) != CollectionKind::None) {
        // A whole array, or a sub-array, of handles. It may be traversed, but
        // LRM 11.3.2 forbids an inline constraint on it (CH11-11, a semantic
        // check for later). There is no element scope to resolve one in, and
        // resolving it in the array's own scope reports every member as
        // unknown.
        return 0;
    }

    if (elem_s && isTraversableType(elem_s)) {
        return elem_s;
    }

    if (is_action_data || !report) {
        // An `action` data field: randomized, and has no members to name.
        return 0;
    }

    if (!elem_s && n_sub) {
        // The subscripted element's type did not resolve; nothing to say.
        return 0;
    }

    m_ctxt->addMarker(
        MarkerSeverityE::Error,
        loc,
        "'%s' is not an action handle, and cannot be traversed; only a "
        "handle, or a data field declared with the 'action' modifier, can be",
        name.c_str());
    return 0;
}

/**
 * The parts of a traversal resolved in the traversed type: the `with` block
 * and the `.x` side of each initializer. The value side of an initializer
 * resolves in the enclosing scope whatever the type turns out to be.
 */
void TaskResolveRefs::resolveTraversalBody(
        ast::ISymbolScope                                   *type_s,
        ast::IConstraintStmt                                *with_c,
        const std::vector<ast::IActionFieldInitializerUP>   &inits) {
    for (std::vector<ast::IActionFieldInitializerUP>::const_iterator
            it=inits.begin(); it!=inits.end(); it++) {
        resolveInitializer(type_s, it->get());
    }
    if (type_s && with_c) {
        m_ctxt->symtab()->pushScope(type_s, ast::SymbolRefPathElemKind::ElemKind_Inline);
        m_ctxt->pushInlineCtxt(type_s);
        DEBUG_ENTER(" ::getWith()");
        with_c->accept(m_this);
        DEBUG_LEAVE(" ::getWith()");
        m_ctxt->popInlineCtxt();
        m_ctxt->symtab()->popScope();
    }
}

/**
 * `.x.y = v` (11.3.1: "initialization assignment patterns can refer to
 * hierarchical paths within the action handle", U3). The value resolves where
 * it is written. The path resolves in the handle's type, `type_s`, and only
 * there: `.x` names a member of the traversed action, never a name of the
 * enclosing scope, so the root is checked against the type before the
 * ordinary resolver, which would fall back outward, sees it. It is recorded
 * as a with-block reference is, relative to the traversed action
 * (ElemKind_Inline).
 *
 * With no type (the handle did not resolve), the path is left unbound: the
 * cause was reported where it is.
 */
void TaskResolveRefs::resolveInitializer(
        ast::ISymbolScope                   *type_s,
        ast::IActionFieldInitializer        *i) {
    if (i->getValue()) {
        i->getValue()->accept(m_this);
    }
    ast::IExprRefPathContext *path = i->getPath();
    if (!type_s || !path || path->getTarget()) {
        return;
    }
    ast::IExprId *root = path->getHier_id()->getElems().at(0)->getId();
    if (!TaskFindPathElem(m_ctxt->getDebugMgr(), m_ctxt->root()).find(
            type_s, root).sym) {
        m_ctxt->addErrorMarker(
            root->getLocation(),
            "'%s' has no member named '%s'",
            type_s->getName().c_str(),
            root->getId().c_str());
        return;
    }
    m_ctxt->symtab()->pushScope(type_s, ast::SymbolRefPathElemKind::ElemKind_Inline);
    m_ctxt->pushInlineCtxt(type_s);
    resolveExprRefPathContext(path);
    visitSlice(path->getSlice());
    m_ctxt->popInlineCtxt();
    m_ctxt->symtab()->popScope();
}

void TaskResolveRefs::visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) {
    DEBUG_ENTER("visitActivityActionHandleTraversal");
    // The full path resolver: an unknown name is reported (PSS002) and the
    // subscripts are walked. This was a root-only lookup that returned
    // silently on a miss (U7/K6).
    i->getTarget()->accept(m_this);

    ast::IExprMemberPathElem *leaf = i->getTarget()->getHier_id()->getElems().back().get();
    ast::IScopeChild *decl = (i->getTarget()->getTarget()) ? leaf->getId()->getDecl() : 0;
    ast::ISymbolScope *type_s = (decl)
        ? traversedType(decl, leaf->getId(), leaf->getSubscript().size(), true) : 0;

    resolveTraversalBody(type_s, i->getWith_c(), i->getInitializers());
    DEBUG_LEAVE("visitActivityActionHandleTraversal");
}

void TaskResolveRefs::visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) {
    DEBUG_ENTER("visitActivityActionTypeTraversal");
    i->getTarget()->accept(m_this);
    ast::ITypeIdentifier *tid = i->getTarget()->getType_id();
    ast::IScopeChild *type_c = (tid && tid->getTarget())
        ? m_ctxt->resolveSymbolPathRef(tid->getTarget()) : 0;
    ast::ISymbolScope *type_s = dynamic_cast<ast::ISymbolScope *>(type_c);
    if (type_s && !isTraversableType(type_s)) {
        // An unknown type was reported by the accept above; this is a known
        // one that is not an action.
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getTarget()->getLocation(),
            "'%s' is not an action type, and cannot be traversed",
            type_s->getName().c_str());
        type_s = 0;
    }
    resolveTraversalBody(type_s, i->getWith_c(), i->getInitializers());
    DEBUG_LEAVE("visitActivityActionTypeTraversal");
}

void TaskResolveRefs::visitConstraintBlock(ast::IConstraintBlock *i) {
    DEBUG_ENTER("visitConstraintBlock (idx=%d)", i->getIndex());
    m_ctxt->symtab()->pushScope(i);
    VisitorBase::visitConstraintBlock(i);
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitConstraintBlock");
}

void TaskResolveRefs::visitConstraintStmtForeach(ast::IConstraintStmtForeach *i) {
    DEBUG_ENTER("visitConstraintStmtForeach %d", i->getSymtab()->getSymtab().size());
    // Resolve symbols in the array path
    i->getExpr()->accept(m_this);

    m_ctxt->symtab()->pushScope(i->getSymtab());
    for (std::vector<ast::IConstraintStmtUP>::const_iterator
        it=i->getConstraints().begin();
        it!=i->getConstraints().end(); it++) {
        (*it)->accept(m_this);
    }
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitConstraintStmtForeach");
}

void TaskResolveRefs::visitConstraintStmtForall(ast::IConstraintStmtForall *i) {
    DEBUG_ENTER("visitConstraintStmtForall");
    // Resolve the quantified type and the optional collection ref-path
    if (i->getType_id()) {
        i->getType_id()->accept(m_this);
    }
    if (i->getRef_path()) {
        i->getRef_path()->accept(m_this);
    }
    // Resolve the iterator variable's own type (a sibling DataTypeUserDefined),
    // in the enclosing scope, so member access through the iterator (`it.field`)
    // can map the iterator to its type's symbol scope.
    if (i->getSymtab()) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getSymtab()->getChildren().begin();
            it!=i->getSymtab()->getChildren().end(); it++) {
            ast::IConstraintStmtField *f =
                dynamic_cast<ast::IConstraintStmtField *>(it->get());
            if (f && f->getType()) {
                f->getType()->accept(m_this);
            }
        }
    }
    m_ctxt->symtab()->pushScope(i->getSymtab());
    for (std::vector<ast::IConstraintStmtUP>::const_iterator
        it=i->getConstraints().begin();
        it!=i->getConstraints().end(); it++) {
        (*it)->accept(m_this);
    }
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitConstraintStmtForall");
}

void TaskResolveRefs::visitExecScope(ast::IExecScope *i) {
    DEBUG_ENTER("visitExecScope");
    pushProcScope(i);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    popProcScope();
    DEBUG_LEAVE("visitExecScope");
}

void TaskResolveRefs::pushProcScope(ast::IScopeChild *s) {
    ProcFrame frame;
    frame.saved = m_proc_pending;
    frame.n_pushed = 0;
    std::vector<PendingProcStmt> kept;
    for (std::vector<PendingProcStmt>::const_iterator
        it=m_proc_pending.begin(); it!=m_proc_pending.end(); it++) {
        // Only this scope stack's: a nested resolution under another
        // iterator must not pick up steps that belong to this one.
        if (it->symtab == m_ctxt->symtab()) {
            m_ctxt->symtab()->pushScope(it->stmt);
            frame.n_pushed++;
        } else {
            kept.push_back(*it);
        }
    }
    m_ctxt->symtab()->pushScope(s);
    frame.n_pushed++;
    m_proc_frames.push_back(frame);
    m_proc_pending.swap(kept);
}

void TaskResolveRefs::popProcScope() {
    for (int32_t k=0; k<m_proc_frames.back().n_pushed; k++) {
        m_ctxt->symtab()->popScope();
    }
    m_proc_pending.swap(m_proc_frames.back().saved);
    m_proc_frames.pop_back();
}

void TaskResolveRefs::walkProcBodies(ast::IScopeChild *i) {
    std::vector<ast::IScopeChild *> bodies;
    ProceduralScopes::bodies(i, bodies);
    for (std::vector<ast::IScopeChild *>::const_iterator
        it=bodies.begin(); it!=bodies.end(); it++) {
        if (*it) {
            m_proc_pending.push_back({i, m_ctxt->symtab()});
            (*it)->accept(m_this);
            m_proc_pending.pop_back();
        }
    }
}

void TaskResolveRefs::visitProceduralStmtIfElse(ast::IProceduralStmtIfElse *i) {
    DEBUG_ENTER("visitProceduralStmtIfElse");
    // The conditions are outside every body.
    for (std::vector<ast::IProceduralStmtIfClauseUP>::const_iterator
        it=i->getIf_then().begin(); it!=i->getIf_then().end(); it++) {
        if ((*it)->getCond()) {
            (*it)->getCond()->accept(m_this);
        }
    }
    walkProcBodies(i);
    DEBUG_LEAVE("visitProceduralStmtIfElse");
}

void TaskResolveRefs::visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) {
    DEBUG_ENTER("visitProceduralStmtMatch");
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    for (std::vector<ast::IProceduralStmtMatchChoiceUP>::const_iterator
        it=i->getChoices().begin(); it!=i->getChoices().end(); it++) {
        if ((*it)->getCond()) {
            (*it)->getCond()->accept(m_this);
        }
    }
    walkProcBodies(i);
    DEBUG_LEAVE("visitProceduralStmtMatch");
}

void TaskResolveRefs::visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) {
    DEBUG_ENTER("visitProceduralStmtWhile");
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    walkProcBodies(i);
    DEBUG_LEAVE("visitProceduralStmtWhile");
}

void TaskResolveRefs::visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) {
    DEBUG_ENTER("visitProceduralStmtRepeatWhile");
    // The condition follows the body but is outside it: a local of the body
    // is not in scope in it.
    walkProcBodies(i);
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    DEBUG_LEAVE("visitProceduralStmtRepeatWhile");
}

/**
 * True if `c` is a field or local variable whose type is a built-in that
 * carries methods -- `string`, or one of the built-in collections.
 *
 * Such a type has no symbol scope to search, so a member access on it is
 * checked against a method list instead of by lookup.  Distinguishing it
 * from a plain `int` is the whole reason a null scope cannot simply be
 * reported as an error.
 */
/**
 * The declared type of `c`, if it is a field or a local variable.
 */
static ast::IDataType *declaredTypeOf(ast::IScopeChild *c) {
    ast::IField *field = dynamic_cast<ast::IField *>(c);
    if (field && field->getType()) {
        return field->getType();
    }

    ast::IProceduralStmtDataDeclaration *var_decl =
        dynamic_cast<ast::IProceduralStmtDataDeclaration *>(c);
    if (var_decl) {
        return var_decl->getDatatype();
    }

    // A call is a value, and the type of that value is what the function
    // returns. Without this every caller of declaredTypeOf answered "no type
    // at all" for a call element, which is not the same as "a type with no
    // members": `f().size()` on a string-returning `f` was reported as
    // "root ref-path element f is not a composite scope" rather than being
    // recognized as a built-in method call, and `f().x` on an int-returning
    // `f` got the same message instead of the scalar one.
    ast::ISymbolFunctionScope *fn = dynamic_cast<ast::ISymbolFunctionScope *>(c);
    if (fn) {
        for (std::vector<ast::IFunctionPrototype *>::const_iterator
            it=fn->getPrototypes().begin(); it!=fn->getPrototypes().end(); it++) {
            if ((*it)->getRtype()) {
                return (*it)->getRtype();
            }
        }
    }

    return 0;
}

/**
 * True if `c` has a scalar type that can have no members at all -- an int, a
 * bit vector, a bool, a chandle.
 *
 * Deliberately a positive test on a short list rather than "anything that
 * failed to produce a scope". The two are not the same, and the difference
 * is the whole reason a member access on an unresolved type must stay quiet:
 * a user-defined type resolves to nothing when one file of a multi-file
 * model is parsed alone, which is normal and not an error. `string` and the
 * built-in collections are excluded because they *do* have members -- see
 * isBuiltinWithMethods().
 */
static bool isScalarWithoutMembers(ast::IScopeChild *c) {
    ast::IDataType *type = declaredTypeOf(c);
    return type
        && (dynamic_cast<ast::IDataTypeInt *>(type)
            || dynamic_cast<ast::IDataTypeBool *>(type)
            || dynamic_cast<ast::IDataTypeChandle *>(type));
}

/**
 * True if `c` has a user-defined type that did not resolve.
 *
 * Such a field has no scope, so a member access on it fails -- but the
 * *reason* has already been reported, as `unknown type '<name>'`, at the
 * declaration. Saying "not a composite scope" as well gives two diagnostics
 * for one cause and points the second one at the use site rather than at the
 * thing the user has to fix.
 *
 * Note this is not the same condition as isScalarWithoutMembers(): that one
 * says the type is known and has no members, this one says the type is not
 * known at all. Only the first is a defect in the reference; the second is a
 * consequence of a defect already reported elsewhere.
 */
/**
 * True if `c` is a function that returns nothing.
 *
 * Such an element has no scope, so a member access on it fails -- but saying
 * "not a composite scope" is the least useful true thing available. The call
 * is diagnosed as an LRM 20.5 violation instead ("returns void, so its result
 * cannot be used as a value"), by checkVoidCallUse, which now runs on every
 * call element rather than only the last. This predicate is what keeps the two
 * from both firing.
 *
 * Note the asymmetry with a *scalar* return: `f()` returning `int` has a type
 * with no members, and gets the same message `int a; a.x` gets. Only `void`
 * has a better thing to say.
 */
static bool isVoidFunction(ast::IScopeChild *c) {
    ast::ISymbolFunctionScope *fn = dynamic_cast<ast::ISymbolFunctionScope *>(c);
    if (!fn || !fn->getPrototypes().size()) {
        return false;
    }
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=fn->getPrototypes().begin(); it!=fn->getPrototypes().end(); it++) {
        if ((*it)->getRtype()) {
            return false;
        }
    }
    return true;
}

static bool hasUnresolvedUserDefinedType(ast::IScopeChild *c) {
    ast::IDataTypeUserDefined *udt =
        dynamic_cast<ast::IDataTypeUserDefined *>(declaredTypeOf(c));
    return udt && (!udt->getType_id() || !udt->getType_id()->getTarget());
}

bool TaskResolveRefs::isBuiltinWithMethods(ast::IScopeChild *c) {
    ast::IDataType *type = declaredTypeOf(c);

    if (!type) {
        return false;
    }

    if (dynamic_cast<ast::IDataTypeString *>(type)) {
        return true;
    }

    ast::IDataTypeUserDefined *udt =
        dynamic_cast<ast::IDataTypeUserDefined *>(type);
    if (udt && udt->getType_id()) {
        // Resolve the reference rather than reading the name the user
        // wrote: a package may declare its own `array`, and the built-in's
        // methods are not its methods.
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(
            TaskGetElemSymbolScope(m_ctxt->getDebugMgr(), m_ctxt->root())
                .resolve(m_ctxt->resolveSymbolPathRef(udt->getType_id()->getTarget())));
        if (builtinCollectionKind(ts) != CollectionKind::None) {
            return true;
        }
    }

    return false;
}


/**
 * The argument counts a prototype will accept.
 *
 * `min` is the number of leading parameters with no default. The LRM requires
 * defaults to be trailing, so this is just the index of the first one that has
 * a default; a model that violates that is not made worse by counting it this
 * way. `max` is -1 when the last parameter is `...`, meaning unbounded.
 */
static void protoArity(ast::IFunctionPrototype *p, int32_t &min, int32_t &max) {
    const std::vector<ast::IFunctionParamDeclUP> &params = p->getParameters();

    min = 0;
    max = (int32_t)params.size();

    for (int32_t ii=0; ii<(int32_t)params.size(); ii++) {
        if (params.at(ii)->getIs_varargs()) {
            // A varargs parameter absorbs any number of arguments, including
            // none, so it neither raises the minimum nor bounds the maximum.
            max = -1;
            break;
        }
        if (!params.at(ii)->getDflt()) {
            min = ii+1;
        }
    }
}

TaskResolveRefs::TypeCat TaskResolveRefs::catOfDataType(ast::IDataType *dt) {
    if (!dt) {
        return TypeCat::Unknown;
    }

    if (dynamic_cast<ast::IDataTypeString *>(dt)) {
        return TypeCat::Str;
    }

    // int, bit and bool are mutually convertible in PSS, and so is an enum
    // with an integer. Lumping them together means this never has an opinion
    // about width or signedness, which is the part that would need real
    // compatibility rules.
    if (dynamic_cast<ast::IDataTypeInt *>(dt)
        || dynamic_cast<ast::IDataTypeBool *>(dt)
        || dynamic_cast<ast::IDataTypeEnum *>(dt)) {
        return TypeCat::Numeric;
    }

    ast::IDataTypeUserDefined *udt = dynamic_cast<ast::IDataTypeUserDefined *>(dt);

    if (udt && udt->getType_id() && udt->getType_id()->getTarget()) {
        ast::IScopeChild *c = m_ctxt->resolveSymbolPathRef(udt->getType_id()->getTarget());

        // Read the declaration straight off the resolved symbol rather than
        // through TaskGetElemSymbolScope. An enum is an INamedScopeChild, not
        // an ITypeScope, so asking that route for a type scope returns null
        // for every enum -- which is why the first version of this classified
        // enum-typed fields as Unknown and the enum branch below was dead.
        // An enum resolves to an ISymbolEnumScope, which is an ISymbolScope
        // and *not* an ISymbolTypeScope -- so neither the type-scope route
        // nor TaskGetElemSymbolScope ever produces an IEnumDecl from one.
        // Two earlier versions of this branch tested for IEnumDecl and could
        // not fire; enum-typed values classified as Unknown and every enum
        // control in the suite passed vacuously. Found by printing the RTTI
        // name of what the path actually resolved to.
        if (dynamic_cast<ast::ISymbolEnumScope *>(c)) {
            return TypeCat::Numeric;
        }

        ast::ISymbolTypeScope *sts = dynamic_cast<ast::ISymbolTypeScope *>(c);
        ast::IScopeChild *decl = sts?sts->getTarget():c;

        if (dynamic_cast<ast::IEnumDecl *>(decl)) {
            return TypeCat::Numeric;
        }

        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(decl);

        // A built-in collection is left Unknown. `list<int>` against an
        // `int` parameter is a genuine mismatch, but "is a composite type"
        // is the wrong thing to say about it -- the element type is what
        // matters -- so the classifier declines rather than says something
        // true and useless.
        //
        // This guard is **currently unreachable**, and the comment is worth
        // more than the code. A parameterized type reference such as
        // `list<int>` does not resolve to a target here at all, so it never
        // enters this branch; collections come out Unknown by falling off
        // the end instead. Neutralizing the guard fails no test for that
        // reason and not because it is harmless -- the collections *are*
        // declared as IStruct in BuiltinsFactory, so the moment a
        // specialized type reference does resolve here, removing this would
        // start calling every collection composite. Kept deliberately, with
        // the tests in test_function_calls.py pinning the behaviour either
        // way. See plan section 35.3.
        if (builtinCollectionKind(ts) != CollectionKind::None) {
            return TypeCat::Unknown;
        }

        if (dynamic_cast<ast::IStruct *>(ts)
            || dynamic_cast<ast::IComponent *>(ts)
            || dynamic_cast<ast::IAction *>(ts)) {
            return TypeCat::Aggregate;
        }
    }

    // chandle, pyobj, a ref type, an unresolved user-defined name.
    return TypeCat::Unknown;
}

TaskResolveRefs::TypeCat TaskResolveRefs::catOfExpr(ast::IExpr *e) {
    if (!e) {
        return TypeCat::Unknown;
    }

    if (dynamic_cast<ast::IExprString *>(e)) {
        return TypeCat::Str;
    }

    if (dynamic_cast<ast::IExprNumber *>(e)
        || dynamic_cast<ast::IExprBool *>(e)) {
        return TypeCat::Numeric;
    }

    if (dynamic_cast<ast::IExprAggrLiteral *>(e)) {
        return TypeCat::Aggregate;
    }

    // A bare name. Anything longer than one element is a member path, whose
    // type needs the walk this classification does not do -- left Unknown.
    ast::IExprRefPathContext *rp = dynamic_cast<ast::IExprRefPathContext *>(e);

    if (rp && !rp->getSlice()
        && rp->getHier_id()->getElems().size() == 1
        && !rp->getHier_id()->getElems().at(0)->getParams()
        && rp->getHier_id()->getElems().at(0)->getSubscript().empty()
        && rp->getTarget()) {
        ast::IScopeChild *c = m_ctxt->resolveSymbolPathRef(rp->getTarget());

        // An enum *item* used as a value, rather than a field of enum type.
        if (dynamic_cast<ast::IEnumItem *>(c)) {
            return TypeCat::Numeric;
        }

        return catOfDataType(declaredTypeOf(c));
    }

    // Arithmetic, comparisons, casts, conditionals, calls, static paths,
    // subscripts, slices, null. All Unknown by design.
    return TypeCat::Unknown;
}


static const char *catName(TaskResolveRefs::TypeCat c);

namespace {

/**
 * The coarse name this diagnostic uses for a category.
 *
 * TaskExprTypeCat draws finer distinctions than the message does -- it tells
 * `int` from `bit` from an enum -- but the categories that *convert freely*
 * are exactly the ones it lumps together as compatible, so naming them apart
 * here would describe a difference the check does not act on.
 */
const char *argCatName(TypeCatE c) {
    switch (c) {
        case TypeCatE::Int:
        case TypeCatE::Bool:
        case TypeCatE::Float:
        case TypeCatE::Enum:      return "numeric";
        case TypeCatE::String:    return "a string";
        case TypeCatE::Aggregate: return "a composite type";
        case TypeCatE::Chandle:   return "a chandle";
        case TypeCatE::Null:      return "null";
        default:                  return "of unknown type";
    }
}

}

void TaskResolveRefs::checkCallArgTypes(
        ast::IExprMemberPathElem  *elem,
        ast::ISymbolFunctionScope *fn) {
    ast::IFunctionPrototype *proto = fn->getPrototypes().front();
    const std::vector<ast::IExprUP> &args = elem->getParams()->getParameters();
    const std::vector<ast::IFunctionParamDeclUP> &params = proto->getParameters();
    TaskExprTypeCat cat(m_ctxt);

    for (uint32_t ii=0; ii<args.size(); ii++) {
        // Arguments past the fixed parameters land on the varargs parameter,
        // which is always last and carries the element type. Stopping at
        // params.size() left every variadic argument unchecked.
        ast::IFunctionParamDecl *p = 0;
        if (ii < params.size()) {
            p = params.at(ii).get();
        } else if (params.size() && params.back()->getIs_varargs()) {
            p = params.back().get();
        }

        if (!p || !p->getType()) {
            continue;
        }

        if (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType) {
            // A `type` parameter takes a type name, and a `ref` parameter
            // takes a handle. Neither is an ordinary value, and neither is
            // modelled well enough here to have an opinion.
            continue;
        }

        TypeCatE want = cat.dataType(p->getType());
        TypeCatE got = cat.expr(args.at(ii).get());

        if (TaskExprTypeCat::compatible(want, got)) {
            continue;
        }

        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            // IExpr carries no location, so this points at the call and
            // names the argument by position instead.
            elem->getId()->getLocation(),
            "argument %d of '%s' is %s, but parameter '%s' is %s",
            ii+1,
            elem->getId()->getId().c_str(),
            argCatName(got),
            p->getName()?p->getName()->getId().c_str():"?",
            argCatName(want));
    }
}

static const char *catName(TaskResolveRefs::TypeCat c) {
    switch (c) {
        case TaskResolveRefs::TypeCat::Numeric:   return "numeric";
        case TaskResolveRefs::TypeCat::Str:       return "a string";
        case TaskResolveRefs::TypeCat::Aggregate: return "a composite type";
        default:                                  return "of unknown type";
    }
}

void TaskResolveRefs::checkCallArity(
        ast::IExprMemberPathElem *elem,
        ast::IScopeChild        *target) {
    // A parameter list is present exactly when the source wrote `(...)` --
    // see AstBuilderInt::mkMemberPathElem -- so this is what distinguishes a
    // call from a plain reference to the same name.
    if (!elem->getParams()) {
        return;
    }

    // A generic constraint is called like a function but is not one: it has no
    // ISymbolFunctionScope and no IFunctionPrototype, so the arity check below
    // would reject every reference as "'x' is not a function". Its parameter
    // list is on the declaration itself (13.1.2), and none of the parameters
    // may be defaulted or variadic, so arity is an exact match.
    {
        int32_t n_params = -1;
        if (ast::IGenericConstraintDeclBool *gc =
                dynamic_cast<ast::IGenericConstraintDeclBool *>(target)) {
            n_params = (int32_t)gc->getParameters().size();
        } else if (ast::IGenericConstraintDeclValue *gv =
                dynamic_cast<ast::IGenericConstraintDeclValue *>(target)) {
            n_params = (int32_t)gv->getParameters().size();
        }
        if (n_params >= 0) {
            int32_t argc = (int32_t)elem->getParams()->getParameters().size();
            if (argc != n_params) {
                m_ctxt->addMarker(
                    MarkerSeverityE::Error,
                    elem->getId()->getLocation(),
                    "%s arguments to constraint '%s': expected %d, got %d",
                    (argc < n_params)?"too few":"too many",
                    elem->getId()->getId().c_str(),
                    n_params,
                    argc);
            }
            return;
        }
    }

    ast::ISymbolFunctionScope *fn =
        dynamic_cast<ast::ISymbolFunctionScope *>(target);

    if (!fn) {
        // Report whenever the callee resolved to *something* that is not a
        // function. The null guard is the whole of the caution needed here: a
        // name whose type never resolved -- the normal state when one file of
        // a multi-file model is parsed alone -- arrives as null, and is
        // diagnosed where the type is named rather than at the call.
        //
        // Built-in and collection methods never reach this line. They are
        // matched against the method list earlier in the loop and `break`
        // there, which is why this condition does not touch `s.size()` or
        // `l.push_back(1)`.
        //
        // This was first written as a positive test on IField and
        // IProceduralStmtDataDeclaration, in the manner of section 29's
        // isScalarWithoutMembers(), on the reasoning that a wider test would
        // catch the built-in methods too. That reasoning was wrong, and a
        // neutralization row is what showed it: widening the test failed no
        // test and no corpus file. The two versions differ on exactly one
        // input -- `S(1)`, where S names a type -- and reporting that is
        // correct. See plan section 34.2.
        if (target) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                elem->getId()->getLocation(),
                "'%s' is not a function",
                elem->getId()->getId().c_str());
        }
        return;
    }

    if (!fn->getPrototypes().size()) {
        // A function whose prototype never made it into the symbol scope.
        // Not an arity question.
        return;
    }

    // Every call element, not only the path's last. `is_last` used to guard
    // this, on the reasoning that only the final element's value is the
    // path's value. It is not: taking a member of a call result is a use of
    // that result, so `f().x` on a void `f` is exactly what LRM 20.5
    // forbids -- and it is the case that produces the *most* useful message.
    //
    // §38.6 recorded the guard as unobservable, and it was, because `f().x`
    // did not resolve at all then. §39 fixed that, at which point the guard's
    // only remaining effect was to suppress a better diagnostic in favour of
    // "root ref-path element f is not a composite scope". The composite-scope
    // branches now stay quiet for a void function instead; see
    // isVoidFunction().
    checkVoidCallUse(elem, fn);

    int32_t argc = (int32_t)elem->getParams()->getParameters().size();

    // Accept if *any* prototype takes this count. PSS has no overloading, so
    // there is normally one; a function declared twice with different
    // signatures leaves two, and that is a duplicate-declaration defect
    // (plan section 31.4) which should not also surface here as a bogus
    // arity error.
    int32_t min = 0, max = 0;

    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=fn->getPrototypes().begin();
        it!=fn->getPrototypes().end(); it++) {
        int32_t p_min, p_max;
        protoArity(*it, p_min, p_max);

        if (argc >= p_min && (p_max < 0 || argc <= p_max)) {
            DEBUG("Call to %s: %d argument(s) accepted",
                elem->getId()->getId().c_str(), argc);
            checkCallArgTypes(elem, fn);
            return;
        }

        if (it == fn->getPrototypes().begin()) {
            min = p_min;
            max = p_max;
        }
    }

    // Report against the first prototype: with no overloading it is the only
    // one, and naming a bound from a signature the user did not write would
    // be worse than naming one from the signature they did.
    if (argc < min) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            elem->getId()->getLocation(),
            "too few arguments to '%s': expected %s%d, got %d",
            elem->getId()->getId().c_str(),
            (max != min)?"at least ":"",
            min,
            argc);
    } else {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            elem->getId()->getLocation(),
            "too many arguments to '%s': expected %s%d, got %d",
            elem->getId()->getId().c_str(),
            (max != min)?"at most ":"",
            max,
            argc);
    }
}

namespace {
    /** Sets a member for the duration of a scope, and puts it back. */
    struct SaveExpr {
        SaveExpr(ast::IExpr *&slot, ast::IExpr *v) : m_slot(slot), m_prev(slot) {
            m_slot = v;
        }
        ~SaveExpr() { m_slot = m_prev; }
        ast::IExpr *&m_slot;
        ast::IExpr *m_prev;
    };
}

// Each path visitor resolves the path, then walks the bit slice, which the
// resolution bodies never reached (F-N5: `x[NOSUCH:0]` was silent). The bodies
// have many early exits, which is why the slice is walked out here.
void TaskResolveRefs::visitSlice(ast::IExprBitSlice *slice) {
    if (!slice) {
        return;
    }
    if (slice->getLhs()) {
        slice->getLhs()->accept(m_this);
    }
    if (slice->getRhs()) {
        slice->getRhs()->accept(m_this);
    }
}

void TaskResolveRefs::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    resolveExprRefPathContext(i);
    visitSlice(i->getSlice());
}

void TaskResolveRefs::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    resolveExprRefPathStatic(i);
    visitSlice(i->getSlice());
}

void TaskResolveRefs::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    resolveExprRefPathStaticRooted(i);
    visitSlice(i->getSlice());
}

void TaskResolveRefs::visitActivitySuper(ast::IActivitySuper *i) {
    DEBUG_ENTER("visitActivitySuper");
    checkSuperStmt(i);
    DEBUG_LEAVE("visitActivitySuper");
}

void TaskResolveRefs::visitProceduralStmtSuper(ast::IProceduralStmtSuper *i) {
    DEBUG_ENTER("visitProceduralStmtSuper");
    checkSuperStmt(i);
    DEBUG_LEAVE("visitProceduralStmtSuper");
}

void TaskResolveRefs::checkSuperStmt(ast::IScopeChild *stmt) {
    // `super;` runs the base type's activity or exec block (Table 27): with
    // no base type there is nothing for it to run. An unresolved base is
    // reported at the declaration.
    ast::ISymbolTypeScope *type_s = TaskResolveRootRef(m_ctxt).contextType();
    ast::ITypeScope *ts = (type_s)
        ? dynamic_cast<ast::ITypeScope *>(type_s->getTarget()) : 0;

    if (type_s && ts && !ts->getSuper_t()) {
        m_ctxt->addErrorMarker(stmt->getLocation(),
            "'super;' is only valid inside a type that has a base type, "
            "and '%s' has none",
            type_s->getName().c_str());
    }
}

void TaskResolveRefs::reportSuperMiss(
        ast::IExprId                                *id,
        const TaskResolveRootRef::SuperResult       &res) {
    typedef TaskResolveRootRef::SuperStatus S;
    switch (res.status) {
        case S::NoType:
            m_ctxt->addErrorMarker(id->getLocation(),
                "'super' is only valid inside a type: an action, component, "
                "struct or other type body");
            break;
        case S::NoBase:
            m_ctxt->addErrorMarker(id->getLocation(),
                "'super' is only valid inside a type that has a base type, "
                "and '%s' has none",
                res.type_s->getName().c_str());
            break;
        case S::NotFound: {
            // A member of the type itself, not inherited, is the likely
            // mistake: `super.x` written for a field the type declares.
            bool own = res.type_s->getSymtab().find(id->getId())
                != res.type_s->getSymtab().end();
            if (own) {
                m_ctxt->addErrorMarker(id->getLocation(),
                    "base type '%s' has no member named '%s'; '%s' is "
                    "declared in '%s' itself, so refer to it without 'super.'",
                    res.base_s->getName().c_str(), id->getId().c_str(),
                    id->getId().c_str(), res.type_s->getName().c_str());
            } else {
                m_ctxt->addErrorMarker(id->getLocation(),
                    "base type '%s' has no member named '%s'",
                    res.base_s->getName().c_str(), id->getId().c_str());
            }
        } break;
        case S::BaseUnresolved:
        case S::Ok:
            break;
    }
}

void TaskResolveRefs::resolveExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext %s", i->getHier_id()->getElems().at(0)->getId()->getId().c_str());

    // Restored on every exit, of which this function has many (see the
    // DEBUG_LEAVE calls below), which is why it is a scope guard and not a
    // pair of assignments.
    SaveExpr save_refpath(m_cur_refpath, i);
    // Find the first path element.
    //
    // A target that is already present was resolved somewhere this pass
    // cannot see -- specifically, at the use site of a template argument,
    // before the expression was copied into the specialization (CL-N2).
    // Re-resolving it here would resolve it in the specialization's scope,
    // which is the generic's declaring scope, and either fail or -- worse --
    // silently find a different declaration of the same name.
    ast::ISymbolRefPath *target = i->getTarget();

    if (!target && i->getIs_super()) {
        // `super.x` searches the base type only (5.2). A miss is reported
        // here: the lexical-miss handling below would suggest, or find, a
        // name the base does not have.
        TaskResolveRootRef::SuperResult res;
        target = TaskResolveRootRef(m_ctxt).resolveSuper(
            i->getHier_id()->getElems().at(0)->getId(), res);
        if (!target) {
            reportSuperMiss(i->getHier_id()->getElems().at(0)->getId(), res);
            DEBUG_LEAVE("visitExprRefPathContext -- super miss");
            return;
        }
    } else if (!target) {
        target = TaskResolveRef(m_ctxt).resolve(
            i->getHier_id()->getElems().at(0)->getId());
    }

    if (!target) {
        const std::string &name = i->getHier_id()->getElems().at(0)->getId()->getId();

        // Already reported here -- an ambiguous import (PSS017) resolves to
        // nothing, and "unknown identifier" on top of it is a cascade.
        if (m_ctxt->wasReported(i->getHier_id()->getElems().at(0)->getId()->getLocation())) {
            DEBUG_LEAVE("visitExprRefPathContext -- already reported");
            return;
        }

        // `this` fails only where there is no enclosing type (a package-level
        // function); "unknown identifier", with a spelling suggestion, would
        // misdescribe that.
        if (name == "this"
                && !i->getHier_id()->getElems().at(0)->getId()->getIs_escaped()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getHier_id()->getElems().at(0)->getId()->getLocation(),
                "'this' is only valid inside a type: an action, component, "
                "struct or other type body");
            DEBUG_LEAVE("visitExprRefPathContext -- this outside a type");
            return;
        }

        // Skip resolution errors for generic constraint parameters
        if (isGenericConstraintParam(name)) {
            DEBUG("Skipping resolution for generic constraint param '%s'", name.c_str());
            DEBUG_LEAVE("visitExprRefPathContext -- generic param");
            return;
        }

        std::string suggestion = findCloseMatch_rr(
            name, dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()));
        if (suggestion.empty() && m_ctxt->symtab()) {
            // getScope() walks backward from the top of the stack it is
            // given and silently *erases* every non-ISymbolScope entry it
            // passes over (by design -- TaskResolveRootRef::resolve() relies
            // on this to converge its root-ref search, and always calls it
            // on a throwaway clone). Calling it directly on the live active
            // stack here corrupted it whenever the innermost frame was a
            // non-ISymbolScope node -- a constraint block, for instance --
            // silently dropping a frame a caller further up (visitConstraintBlock)
            // still owns and will pop itself, eventually popping the wrong
            // scope or an empty stack (E7-D14). Use a scratch clone instead,
            // exactly as TaskResolveRootRef::resolve() does for the same
            // reason.
            ISymbolTableIteratorUP scratch(m_ctxt->cloneSymtab());
            if (scratch) {
                suggestion = findCloseMatch_rr(name, scratch->getScope());
            }
        }
        // A core-library name is the one case where "unknown identifier" is
        // true but actively misleading: the name exists, the model just did
        // not import the package that declares it. Preferred over the
        // edit-distance suggestion, which is a guess where this is a fact.
        std::string core_pkg = findCoreLibraryPackage(
            dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()), name);

        if (!core_pkg.empty()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getHier_id()->getElems().at(0)->getId()->getLocation(),
                "unknown identifier '%s'; declared in %s -- add "
                "'import %s::*;'",
                name.c_str(),
                core_pkg.c_str(),
                core_pkg.c_str());
        } else if (suggestion.empty()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getHier_id()->getElems().at(0)->getId()->getLocation(),
                "unknown identifier '%s'",
                name.c_str());
        } else {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getHier_id()->getElems().at(0)->getId()->getLocation(),
                "unknown identifier '%s'; did you mean '%s'?",
                name.c_str(),
                suggestion.c_str());
        }

        DEBUG_LEAVE("visitExprRefPathContext -- fail");
        return;
    }

    // Set root reference. Guarded against the already-resolved case above:
    // setTarget owns what it is given, so handing it back the pointer it
    // already holds would free it and leave the node dangling.
    if (target != i->getTarget()) {
        i->setTarget(target);
    }

    ast::IScopeChild *target_c = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), 
        m_ctxt->root(),
        m_ctxt->inlineCtxt()).resolve(target);
    ast::ISymbolScope *target_s = 0;

    // Record what each element binds to (pss-scrambler FR-001). The root is
    // resolved here, with the inline context in hand, which is the only place
    // a `with { ... }` field can be followed back to its declaration.
    i->getHier_id()->getElems().at(0)->getId()->setDecl(target_c);
    
    if (target_c) {
        target_s = TaskGetElemSymbolScope(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target_c);
    }

    DEBUG("target_c=%p target_s=%p", target_c, target_s);

    // Check if target_c is a field or local variable with a built-in type that has methods (e.g., string)
    bool is_builtin_with_methods =
        (!target_s && target_c && isBuiltinWithMethods(target_c));

    // Tracked separately from the flag above because the two built-in
    // families are checked differently below: `string` carries real
    // prototypes and is resolved against them, while a collection method is
    // still only name-checked.
    bool is_string_target = is_builtin_with_methods
        && dynamic_cast<ast::IDataTypeString *>(declaredTypeOf(target_c));

    // The element index at which a member is checked against the built-in
    // method list rather than looked up in a scope: the one directly after
    // whichever element turned out to have a built-in type. For the root
    // that is 1; the advance step below sets it when a *later* element does.
    int32_t builtin_method_ii = is_builtin_with_methods?1:-1;

    if (!target_s && !is_builtin_with_methods && i->getHier_id()->getElems().size() > 1) {
        if (target_c && isVoidFunction(target_c)) {
            // checkVoidCallUse has the better message for this; see
            // isVoidFunction(). It has to be invoked here rather than left to
            // the loop below, because this branch returns before the loop
            // runs -- suppressing the composite-scope message without also
            // making the call reported nothing at all.
            checkCallArity(i->getHier_id()->getElems().at(0).get(), target_c);
        } else if (target_c && hasUnresolvedUserDefinedType(target_c)) {
            // The root's type never resolved, and `unknown type '<name>'` was
            // already reported at its declaration. Reporting again here gives
            // two errors for one cause and points the second at the use site
            // rather than at the thing to fix. Return regardless: with no
            // scope there is nothing to search the rest of the path in, and
            // falling through raises a *different* error from the loop.
            DEBUG("Root %s has an unresolved type; "
                "already reported at its declaration",
                i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
        } else {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                i->getHier_id()->getElems().at(0)->getId()->getLocation(),
                "root ref-path element %s is not a composite scope",
                i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
        }

        DEBUG_LEAVE("visitExprRefPathContext -- fail");
        return;
    }

    // Target already points to the first elem
    i->getHier_id()->getElems().at(0)->setTarget(-1);

    for (uint32_t ii=0; ii<i->getHier_id()->getElems().size(); ii++) {
        ast::IExprMemberPathElem *elem = i->getHier_id()->getElems().at(ii).get();

        DEBUG("ii=%0d %s: subscript=%d params=%p", 
            ii, 
            elem->getId()->getId().c_str(),
            elem->getSubscript().size(), 
            elem->getParams());

        // Ensure we resolve expression references in function parameters
        if (elem->getParams()) {
            DEBUG_ENTER("Resolve parameter references");
            for (std::vector<ast::IExprUP>::const_iterator
                it=elem->getParams()->getParameters().begin();
                it!=elem->getParams()->getParameters().end(); it++) {
                (*it)->accept(m_this);
            }
            DEBUG_LEAVE("Resolve parameter references");
        }

        for (std::vector<ast::IExprUP>::const_iterator
            it=elem->getSubscript().begin();
            it!=elem->getSubscript().end(); it++) {
            (*it)->accept(m_this);
        }

        if (!ii && elem->getParams()) {
            // The root element is itself the call -- `g(1,2,3)`. Later
            // elements are checked once TaskFindPathElem has resolved them.
            if (m_template_depth) {
                TaskTemplateCheck(m_ctxt).checkPure(target_c, elem);
            }
        }

//        if (!ii) {
            if (ii+1 < i->getHier_id()->getElems().size() && elem->getSubscript().size()) {
                if (hasSliceSubscript_rr(elem)) {
                    m_ctxt->addErrorMarker(
                        elem->getId()->getLocation(),
                        "member selection is not permitted on a slice of '%s'",
                        elem->getId()->getId().c_str());
                    break;
                }
                if (elem->getSubscript().size() > 1) {
                    DEBUG("Multi-dim array subscript");
                }
                target_s = TaskGetSubscriptSymbolScope(
                    m_ctxt->getDebugMgr(), m_ctxt->root(),
                    elem->getSubscript().size()).resolve(
                        target_c
                    );
            }
            if (!ii) {
                // A call whose callee is the root of the path -- a plain
                // `f(1)`. The member-call form is checked further down,
                // where the element's own target is resolved.
                checkCallArity(elem, target_c);
                continue;
            }
//        }

        DEBUG("Search for elem=%s target_s=%s", 
            elem->getId()->getId().c_str(),
            (target_s)?target_s->getName().c_str():"null");

        if (target_s && target_s->getOpaque()) {
            DEBUG("Note: scope is opaque ; ending hierarchical search");
            break;
        }

        // Special handling for string and collection methods
        if (!target_s && is_builtin_with_methods && ii == builtin_method_ii) {
            // This is a method call on a built-in type - validate method name
            std::string method_name = elem->getId()->getId();
            // A string method is looked up in the `string` pseudo-type, which
            // carries a real prototype for each one; a collection method is
            // still only name-checked (P3-X6d covers strings only).
            ast::IScopeChild *proto = 0;
            bool found = false;
            if (is_string_target) {
                ast::ISymbolScope *string_s = builtinStringScope_rr(m_ctxt->root());
                if (string_s) {
                    proto = TaskFindPathElem(
                        m_ctxt->getDebugMgr(),
                        m_ctxt->root()).find(string_s, elem->getId()).sym;
                    found = (proto != 0);
                }
            } else {
                found = (builtinMethods().find(method_name)
                            != builtinMethods().end());
            }

            if (found) {
                DEBUG("Valid built-in method: %s", method_name.c_str());
                // -2 marks "resolved, but not to an index in the enclosing
                // scope". The element path stops here either way, so the
                // prototype is used for checking only and is not recorded.
                elem->setTarget(-2);
                // A `string` method binds to its prototype; a collection
                // method has none, and stays null (FR-001-Q1: "builtin").
                elem->getId()->setDecl(proto);
                if (elem->getParams()) {
                    DEBUG_ENTER("Resolve built-in method parameters");
                    for (auto it=elem->getParams()->getParameters().begin();
                        it!=elem->getParams()->getParameters().end(); it++) {
                        (*it)->accept(m_this);
                    }
                    DEBUG_LEAVE("Resolve built-in method parameters");
                    if (proto) {
                        // checkCallArity never reaches a built-in method --
                        // the loop breaks here -- so this site is the only
                        // place a `string` method's real signature gets
                        // checked. Additive, not a second opinion.
                        TaskCheckCallArgs(m_ctxt).check(proto, elem);
                        if (m_template_depth) {
                            TaskTemplateCheck(m_ctxt).checkPure(proto, elem);
                        }
                    }
                }
                break;
            } else {
                m_ctxt->addErrorMarker(
                    elem->getId()->getLocation(),
                    "unknown method '%s' on built-in type",
                    method_name.c_str());
                break;
            }
        }

        if (!target_s) {
            // The enclosing scope is unresolved -- most often because the
            // root element's type is unknown, which is the normal state when
            // one file of a multi-file model is parsed on its own.
            //
            // This is reachable even though the pre-loop check above rejects
            // a null target_s: the subscript step earlier in this loop
            // re-assigns target_s from TaskGetSubscriptSymbolScope(), which
            // returns null for an element of unknown type. Passing that null
            // to TaskFindPathElem::find() dereferences it immediately.
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                elem->getId()->getLocation(),
                "cannot resolve '%s': the enclosing scope is unknown",
                elem->getId()->getId().c_str());
            DEBUG_LEAVE("visitExprRefPathContext -- unresolved enclosing scope");
            return;
        }

        TaskFindPathElem::Result res = TaskFindPathElem(
            m_ctxt->getDebugMgr(),
            m_ctxt->root()).find(
                target_s,
                elem->getId()
            );

        std::unordered_map<std::string, int32_t>::const_iterator it =
            target_s->getSymtab().find(elem->getId()->getId());
        
        if (!res.sym) {
            bool is_collection_method = false;
            // Not a name test: `n.rfind("set", 0) == 0` matched `setup_s`,
            // and every collection method was then available on it.
            auto isCollectionScope = [](ast::ISymbolScope *s) -> bool {
                return builtinCollectionKind(s) != CollectionKind::None;
            };
            if (isCollectionScope(target_s)) {
                DEBUG("Collection method check: target_s name='%s' method='%s'",
                    target_s->getName().c_str(), elem->getId()->getId().c_str());
                const std::string &mname = elem->getId()->getId();
                if (collectionMethods().count(mname)) {
                    is_collection_method = true;
                    elem->setTarget(-2);
                    if (elem->getParams()) {
                        for (auto pit=elem->getParams()->getParameters().begin();
                            pit!=elem->getParams()->getParameters().end(); pit++) {
                            (*pit)->accept(m_this);
                        }
                    }
                    break;
                }
            }
            if (!is_collection_method) {
            DEBUG("Not collection method. target_s=%p name='%s'",
                target_s, target_s ? target_s->getName().c_str() : "<null>");
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "Failed to find elem %s", 
                elem->getId()->getId().c_str());
            DEBUG("ERROR: Failed to find elem %s (ii=%d)", 
                elem->getId()->getId().c_str(),
                ii);
            break;
            }
        } else {
            DEBUG("NOTE: Found sub-element %s", elem->getId()->getId().c_str());
            elem->setTarget(res.idx);
            elem->setSuper(res.super_idx);
            elem->getId()->setDecl(res.sym);

            // A member call -- `comp.f(1)`, `pkg::f(1)`.
            checkCallArity(elem, res.sym);

            // The receiver is in hand here, which is what the §21.14.1 field
            // names need: they are resolved against the register's value type,
            // not against the callee.
            checkRegFieldRefs(elem, target_s);

            // Resolve name references for parameter values
            if (elem->getParams()) {
                elem->getParams()->accept(m_this);
                if (m_template_depth) {
                    TaskTemplateCheck(m_ctxt).checkPure(res.sym, elem);
                }
            }

            if (ii+1 < i->getHier_id()->getElems().size()) {
                target_c = res.sym;
                target_s = TaskGetElemSymbolScope(
                    m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(
                        target_c
                    );
                if (!target_s) {
                    // This element has no scope to search for the next one.
                    // Until now that was a DEBUG_ERROR and a break -- debug
                    // chatter, no marker, exit 0 -- so `s.a.nosuch` with `a`
                    // an int linked cleanly. Only the *root* of the path was
                    // ever reported (above); everything after it fell to here.
                    if (isBuiltinWithMethods(target_c)) {
                        // `a` is a string or a built-in collection: it has no
                        // scope but it does have methods. Check the next
                        // element against the method list, exactly as the
                        // root case does.
                        is_builtin_with_methods = true;
                        is_string_target = (dynamic_cast<ast::IDataTypeString *>(
                            declaredTypeOf(target_c)) != 0);
                        builtin_method_ii = ii+1;
                        DEBUG("Element %s is a built-in with methods; "
                            "checking %s against the method list",
                            elem->getId()->getId().c_str(),
                            i->getHier_id()->getElems().at(ii+1)
                                ->getId()->getId().c_str());
                        continue;
                    }

                    if (isScalarWithoutMembers(target_c)) {
                        m_ctxt->addMarker(
                            MarkerSeverityE::Error,
                            i->getHier_id()->getElems().at(ii+1)
                                ->getId()->getLocation(),
                            "ref-path element %s is not a composite scope",
                            elem->getId()->getId().c_str());
                    } else {
                        // A type that produced no scope for some other
                        // reason -- most often a user-defined type that did
                        // not resolve, which is the normal state when one
                        // file of a multi-file model is parsed on its own.
                        // Reporting it here would turn that into an error;
                        // the unresolved type is diagnosed where it is
                        // declared, if at all.
                        DEBUG("No scope for %s, but its type is not a scalar; "
                            "not reporting",
                            elem->getId()->getId().c_str());
                    }
                    break;
                }

                if (elem->getSubscript().size()) {
                    if (hasSliceSubscript_rr(elem)) {
                        m_ctxt->addErrorMarker(
                            elem->getId()->getLocation(),
                            "member selection is not permitted on a slice of '%s'",
                            elem->getId()->getId().c_str());
                        break;
                    }
                    if (elem->getSubscript().size() > 1) {
                        // Only the first subscript selects the element scope
                        // searched for the next path element. Not an error:
                        // a collection of collections takes two.
                        DEBUG("TODO: multi-subscript element scope");
                    }
                    target_s = TaskGetSubscriptSymbolScope(
                        m_ctxt->getDebugMgr(), m_ctxt->root(),
                        elem->getSubscript().size()).resolve(
                            target_s
                        );
                }
                DEBUG("Next target_s: %s", target_s->getName().c_str());
            }
        }
    }

    if (target_c) {
        m_ctxt->addRef(
            i->getHier_id()->getElems().front()->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }

    DEBUG_LEAVE("visitExprRefPathContext");
}

void TaskResolveRefs::visitActivityDecl(ast::IActivityDecl *i) {
    DEBUG_ENTER("visitActivityDecl");
    VisitorBase::visitActivityDecl(i);
    DEBUG_LEAVE("visitActivityDecl");
}

void TaskResolveRefs::visitActivitySequence(ast::IActivitySequence *i) {
    DEBUG_ENTER("visitActivitySequence");
    VisitorBase::visitActivitySequence(i);
    DEBUG_LEAVE("visitActivitySequence");
}

void TaskResolveRefs::resolveActivityScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("resolveActivityScope");
    m_ctxt->symtab()->pushScope(i);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin(); it!=i->getChildren().end(); it++) {
        visitMergedScopeChild(it->get());
    }
    std::vector<ast::IScopeChild *> bodies;
    ActivityScopes::bodies(i, bodies);
    for (std::vector<ast::IScopeChild *>::const_iterator
        it=bodies.begin(); it!=bodies.end(); it++) {
        if (*it) {
            (*it)->accept(m_this);
        }
    }
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("resolveActivityScope");
}

void TaskResolveRefs::visitActivityForeach(ast::IActivityForeach *i) {
    DEBUG_ENTER("visitActivityForeach");
    // The collection is written outside the loop, so it cannot see the loop's
    // own variables. The index of `foreach (a[j])` is not part of it: the
    // builder lifts `[j]` out of the path (F4).
    if (i->getPath()) {
        i->getPath()->accept(m_this);
    }
    // Typed now that the collection has resolved, so `foreach (h : handles)
    // { h; }` traverses an action handle rather than an `int` (K3).
    typeLoopIterator(i, i->getIt_id(), i->getPath());
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityForeach");
}

void TaskResolveRefs::visitActivityRepeatCount(ast::IActivityRepeatCount *i) {
    DEBUG_ENTER("visitActivityRepeatCount");
    if (i->getCount()) {
        i->getCount()->accept(m_this);
    }
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityRepeatCount");
}

void TaskResolveRefs::visitActivityRepeatWhile(ast::IActivityRepeatWhile *i) {
    DEBUG_ENTER("visitActivityRepeatWhile");
    if (i->getCond()) {
        i->getCond()->accept(m_this);
    }
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityRepeatWhile");
}

void TaskResolveRefs::visitActivityReplicate(ast::IActivityReplicate *i) {
    DEBUG_ENTER("visitActivityReplicate");
    if (i->getCount()) {
        i->getCount()->accept(m_this);
    }
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityReplicate");
}

void TaskResolveRefs::visitActivityIfElse(ast::IActivityIfElse *i) {
    DEBUG_ENTER("visitActivityIfElse");
    if (i->getCond()) {
        i->getCond()->accept(m_this);
    }
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityIfElse");
}

void TaskResolveRefs::visitActivitySelect(ast::IActivitySelect *i) {
    DEBUG_ENTER("visitActivitySelect");
    for (std::vector<ast::IActivitySelectBranchUP>::const_iterator
        it=i->getBranches().begin(); it!=i->getBranches().end(); it++) {
        if ((*it)->getGuard()) {
            (*it)->getGuard()->accept(m_this);
        }
        if ((*it)->getWeight()) {
            (*it)->getWeight()->accept(m_this);
        }
    }
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivitySelect");
}

void TaskResolveRefs::visitActivityMatch(ast::IActivityMatch *i) {
    DEBUG_ENTER("visitActivityMatch");
    if (i->getCond()) {
        i->getCond()->accept(m_this);
    }
    for (std::vector<ast::IActivityMatchChoiceUP>::const_iterator
        it=i->getChoices().begin(); it!=i->getChoices().end(); it++) {
        if ((*it)->getCond()) {
            (*it)->getCond()->accept(m_this);
        }
    }
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityMatch");
}

void TaskResolveRefs::visitActivityAtomicBlock(ast::IActivityAtomicBlock *i) {
    DEBUG_ENTER("visitActivityAtomicBlock");
    resolveActivityScope(i);
    DEBUG_LEAVE("visitActivityAtomicBlock");
}

void TaskResolveRefs::visitMonitorActivityEventually(ast::IMonitorActivityEventually *i) {
    DEBUG_ENTER("visitMonitorActivityEventually");
    resolveActivityScope(i);
    DEBUG_LEAVE("visitMonitorActivityEventually");
}


/**
 * True if `c` is a template type that has not been specialized -- the generic
 * itself, which cannot stand in for one of its instances.
 *
 * A specialization's own scope carries `specialized`, so this is false for
 * `P<8>` and for references written inside a specialized copy.
 */
static bool isUnspecializedGeneric(ast::IScopeChild *c) {
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(c);
    ast::ITypeScope *td = ts?dynamic_cast<ast::ITypeScope *>(ts->getTarget()):0;
    return td
        && td->getParams()
        && !td->getParams()->getSpecialized()
        && td->getParams()->getParams().size();
}

void TaskResolveRefs::resolveExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic size=%d", i->getBase().size());
    // Already resolved at a use site this pass cannot see -- see the matching
    // note in visitExprRefPathContext. `bit[8] a[c_c::N]` is the case:
    // the path is resolved where it is written, then copied into the builtin
    // `array` generic's specialization, where `c_c` does not exist.
    if (i->getTarget()) {
        DEBUG_LEAVE("visitExprRefPathStatic -- already resolved");
        return;
    }
    ast::ISymbolRefPath *target = 0;
    {
        // `::K` resolves its first element in the global package only
        // (18.1.3, F20); `::NOPE` used to be accepted silently (ND-2).
        //
        // `target` deliberately assigns to the outer declaration rather than
        // shadowing it. It used to be re-declared here, which left the outer
        // one at 0 for the `if (target)` below -- so the cross-file dependency
        // edge (addRef) was never recorded for any static reference path.
        ast::IScopeChild *target_s = 0;
        bool in_pyref = false;
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin();
            it!=i->getBase().end(); it++) {
            if (it==i->getBase().begin()) {
                target = i->getIs_global()
                    ? TaskResolveRef(m_ctxt).resolveGlobal((*it)->getId())
                    : TaskResolveRef(m_ctxt).resolve((*it)->getId());

                if (target) {
                    // Bound before specialization, so a generic names the
                    // generic's declaration rather than a copy (FR-001).
                    (*it)->getId()->setDecl(m_ctxt->resolveSymbolPathRef(target));
                }
                
                if (!target) {
                    // As in visitExprRefPathContext: name the missing import
                    // when the symbol is a core-library one.
                    std::string core_pkg = findCoreLibraryPackage(
                        dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()),
                        (*it)->getId()->getId());

                    if (!core_pkg.empty()) {
                        addMarker(
                            MarkerSeverityE::Error,
                            (*it)->getId()->getLocation(),
                            "failed to resolve symbol %s; declared in %s -- "
                            "add 'import %s::*;'",
                            (*it)->getId()->getId().c_str(),
                            core_pkg.c_str(),
                            core_pkg.c_str());
                    } else {
                        addMarker(
                            MarkerSeverityE::Error,
                            (*it)->getId()->getLocation(),
                            "failed to resolve symbol %s",
                            (*it)->getId()->getId().c_str());
                    }
                    break;
                }

                if ((*it)->getParams()) {
                    DEBUG("Ref elem %d is parameterized", (it-i->getBase().begin()));

                    // Resolve the argument values *here*, at the use site,
                    // before specializing -- the same thing
                    // TaskResolveRef::visitTypeIdentifier does for a type
                    // reference. Without it the arguments carry no resolved
                    // target into TaskBuildParamValList, which then resolves
                    // them wherever it happens to be: the generic's declaring
                    // package. `Q<s_s>::nbytes` written in package `p` bound
                    // `q::s_s` when both packages declared an `s_s`, silently
                    // and with no diagnostic, while the field-typed form
                    // `Q<s_s> q;` bound `p::s_s` from the same source line.
                    for (std::vector<ast::ITemplateParamValueUP>::const_iterator
                        v_it=(*it)->getParams()->getValues().begin();
                        v_it!=(*it)->getParams()->getValues().end(); v_it++) {
                        (*v_it)->accept(m_this);
                    }

                    // Build out parameter value list
                    target = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                            target,
                            (*it)->getParams(),
                            (*it)->getId()->getLocation());

                    // TODO: do we need to delete target?

                    if (!target) {
                        // specialize() returns null once it has reported an
                        // argument error -- a wrong argument count, a
                        // restriction violation. Continuing dereferenced the
                        // null path and segfaulted, so `P<int>::nbytes` (one
                        // argument too few) crashed where the field-typed form
                        // reported "no value supplied for template parameter".
                        break;
                    }
                }

                target_s = m_ctxt->resolveSymbolPathRef(target);

                if ((*it)->getParams()) {
                    DEBUG("Ref elem is parameterized");
                } else if (isUnspecializedGeneric(target_s)) {
                    // A generic named with no argument list at all --
                    // `P::nbytes` rather than `P<8>::nbytes`. Nothing above
                    // catches it: the specialize() step that validates
                    // arguments only runs when there *are* arguments, so the
                    // path resolved straight to the generic and every member
                    // of it looked available.
                    addMarker(
                        MarkerSeverityE::Error,
                        (*it)->getId()->getLocation(),
                        "template type '%s' requires a template argument list",
                        (*it)->getId()->getId().c_str());
                    target = 0;
                    break;
                }

                if (!in_pyref) {
                    in_pyref |= TaskIsPyRef(m_ctxt->getDebugMgr(), m_ctxt->root()).check(target_s);
                    if (in_pyref) {
                        target->setPyref_idx(0);
                    } else {
                    }
                }
            } else if (!in_pyref) {
                // Visit the element to resolve internal references (its own
                // template arguments, if any)
                (*it)->accept(m_this);

                // ...then resolve the element *within* the preceding one,
                // which is what the TODO that used to stand here asked for.
                // Until now the accept() above was the whole of it and its
                // result was discarded, so `Q<ok_s>::nosuch` linked cleanly:
                // only the root of a static path was ever checked.
                ast::ISymbolScope *scope_s =
                    dynamic_cast<ast::ISymbolScope *>(target_s);

                if (!scope_s) {
                    // The preceding element is not a scope -- a static path
                    // through a field, say. Nothing to look the name up in,
                    // and the reason is already diagnosed where that element
                    // resolved, so stop rather than report a second error.
                    DEBUG("Preceding element is not a scope; cannot check %s",
                        (*it)->getId()->getId().c_str());
                    break;
                }

                TaskFindPathElem::Result res = TaskFindPathElem(
                    m_ctxt->getDebugMgr(),
                    m_ctxt->root()).find(scope_s, (*it)->getId());

                if (!res.sym) {
                    addMarker(
                        MarkerSeverityE::Error,
                        (*it)->getId()->getLocation(),
                        "'%s' has no member named '%s'",
                        scope_s->getName().c_str(),
                        (*it)->getId()->getId().c_str());
                    target = 0;
                    break;
                }

                target_s = res.sym;
                (*it)->getId()->setDecl(res.sym);

                if (res.super_idx == 0) {
                    target->getPath().push_back({
                        ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
                        res.idx});

                    if ((*it)->getParams()) {
                        // A qualified generic: `std_pkg::sizeof_s<T>::nbits`.
                        // Only the first element's arguments used to be
                        // applied, so this bound the *generic's* members --
                        // sizeof_s's placeholder -1 -- and the argument list
                        // was resolved and then dropped. Specialize exactly
                        // as the first element does; the arguments were
                        // resolved at the use site by the accept() above.
                        target = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                            target,
                            (*it)->getParams(),
                            (*it)->getId()->getLocation());
                        if (!target) {
                            break;
                        }
                        target_s = m_ctxt->resolveSymbolPathRef(target);
                    }
                } else {
                    // The member is inherited. A symbol path has no way to
                    // encode a step through a base type --
                    // TaskResolveSymbolPathRef leaves ElemKind_Super as a
                    // TODO -- so extending it with the base's child index
                    // would resolve to whatever child sits at that index in
                    // the derived type. Leave the path at the enclosing type;
                    // the member is checked either way, which is what this
                    // branch is here for.
                    DEBUG("Member %s is inherited (super_idx=%d); path not extended",
                        (*it)->getId()->getId().c_str(), res.super_idx);
                }
            } else {
                DEBUG("element is inside a pyref path");
            }
        }
        i->setTarget(target);
    }

    if (target) {
        // Reached for the first time now that `target` is no longer shadowed
        // above. It had never run, so the null check on target_c had never
        // been needed -- a path can resolve to a reference the symbol-path
        // resolver then declines to follow, and this would have dereferenced
        // it.
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        if (target_c) {
            m_ctxt->addRef(
                i->getBase().front()->getId()->getLocation().fileid,
                target_c->getLocation().fileid);
        }
    }
    DEBUG_LEAVE("visitExprRefPathStatic");
}

void TaskResolveRefs::resolveExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("visitExprRefPathStaticRooted %s",
        i->getLeaf()->getElems().at(0)->getId()->getId().c_str());

    // Set here as well as in visitExprRefPathContext: `p::f(1);` is a
    // standalone statement too, and a qualified name builds a *different*
    // expression node. Setting it in only one of the two made every
    // statement-position call through a package qualifier look like an
    // operand, and three tests that had nothing to do with void returns
    // started failing on `p::f(1);` and `p::m(1,2);`.
    SaveExpr save_refpath(m_cur_refpath, i);
    // Resolve the root. `::p::f()` has a root, `::p`, which resolves in the
    // global package like any `::` path (resolveExprRefPathStatic), and takes
    // the general branch. Only `::f()` -- no root elements -- looks its leaf
    // up in the global package here. This used to be done for both, so
    // `::p::f()` looked for `f` among the globals (A-N2).
    if (i->getRoot()->getIs_global() && !i->getRoot()->getBase().size()) {
        ast::IExprId *id = i->getLeaf()->getElems().at(0)->getId();
        DEBUG("Global reference -- first find leaf %s", id->getId().c_str());
        std::unordered_map<std::string,int32_t>::const_iterator it;
        const std::unordered_map<std::string,int32_t> &symtab = 
            m_ctxt->symtab()->getRootScope()->getSymtab();
        
        if ((it=symtab.find(id->getId())) == symtab.end()) {
            m_ctxt->addErrorMarker(id->getLocation(),
                "unknown identifier '%s' in the global package",
                id->getId().c_str());
        } else {
            ast::ISymbolRefPath *ref = 
                m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
            ast::SymbolRefPathElem elem;
            elem.kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;
            elem.idx = it->second;
            ref->getPath().push_back(elem);
            i->getRoot()->setTarget(ref);
            id->setDecl(m_ctxt->resolveSymbolPathRef(ref));
        }
    } else {
        i->getRoot()->accept(m_this);

        if (!i->getRoot()->getTarget()) {
            DEBUG_LEAVE("visitExprRefPathStaticRooted -- failed root resolution");
            return;
        }

        i->getLeaf()->accept(m_this);

        if (i->getRoot()->getTarget()->getPyref_idx() != -1) {
            // The root ends in a Python-type reference
            DEBUG("Root (static) reference has a Python component");
        } else {
            DEBUG("Root (static) reference does not have a Python component");
            resolveStaticRootedLeaf(i);
        }
    }

    DEBUG_LEAVE("visitExprRefPathStaticRooted");
}

void TaskResolveRefs::resolveStaticRootedLeaf(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("resolveStaticRootedLeaf");

    // P3-X6e. The leaf of a qualified reference used to be visited but never
    // looked up *against its root*, so `p::g(1,2,3)` reached no call site and
    // was neither arity-checked nor reported when `g` did not exist at all.
    ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(i->getRoot()->getTarget());

    if (!target_c) {
        DEBUG_LEAVE("resolveStaticRootedLeaf -- root path does not resolve");
        return;
    }

    ast::ISymbolScope *target_s = TaskGetElemSymbolScope(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target_c);

    if (!target_s) {
        // The root names something that is not a scope to look inside. That is
        // reportable in its own right, but not here -- this path is also taken
        // by references the resolver models loosely, and guessing would turn
        // every one of them into a spurious error.
        DEBUG_LEAVE("resolveStaticRootedLeaf -- root is not a scope");
        return;
    }

    for (uint32_t ii=0; ii<i->getLeaf()->getElems().size(); ii++) {
        ast::IExprMemberPathElem *elem = i->getLeaf()->getElems().at(ii).get();

        TaskFindPathElem::Result res = TaskFindPathElem(
            m_ctxt->getDebugMgr(),
            m_ctxt->root()).find(target_s, elem->getId());

        if (!res.sym) {
            // Same wording as the member-path loop above: one phrasing for
            // one diagnosis, whether the receiver was reached through a
            // qualified path or a member path.
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "'%s' has no member named '%s'",
                target_s->getName().c_str(),
                elem->getId()->getId().c_str());
            break;
        }

        elem->setTarget(res.idx);
        elem->setSuper(res.super_idx);
        elem->getId()->setDecl(res.sym);

        checkCallArity(elem, res.sym);

        if (elem->getParams()) {
            elem->getParams()->accept(m_this);
            if (m_template_depth) {
                TaskTemplateCheck(m_ctxt).checkPure(res.sym, elem);
            }
        }

        for (std::vector<ast::IExprUP>::const_iterator
            it=elem->getSubscript().begin();
            it!=elem->getSubscript().end(); it++) {
            (*it)->accept(m_this);
        }

        if (ii+1 < i->getLeaf()->getElems().size()) {
            target_c = res.sym;
            target_s = TaskGetElemSymbolScope(
                m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target_c);
            if (!target_s) {
                DEBUG("Element %s is not a composite scope -- stop",
                    elem->getId()->getId().c_str());
                break;
            }
        }
    }

    DEBUG_LEAVE("resolveStaticRootedLeaf");
}

void TaskResolveRefs::visitExtendEnum(ast::IExtendEnum *i) {
    DEBUG_ENTER("visitExtendEnum");
    DEBUG("Note: Skip during core symbol resolution");
    DEBUG_LEAVE("visitExtendEnum");
}

void TaskResolveRefs::visitExtendType(ast::IExtendType *i) {
    DEBUG_ENTER("visitExtendType");
    DEBUG("Note: Skip during core symbol resolution");
    DEBUG_LEAVE("visitExtendType");
}

void TaskResolveRefs::visitField(ast::IField *i) {
    DEBUG_ENTER("visitField %s", i->getName()->getId().c_str());
    if (i->getType()) {
        i->getType()->accept(m_this);
    }
    if (i->getInit()) {
        i->getInit()->accept(m_this);

        // PSS115. §4.7: a template whose special elements reference
        // non-constants is not a constant expression, so it cannot initialize
        // a `const` field. Checked after the descent above, which is what
        // computes `is_const`.
        if ((i->getAttr() & ast::FieldAttr::Const) != ast::FieldAttr::NoFlags) {
            checkConstTemplate(i->getInit(), i->getName()->getLocation());
        }
    }
    // A handle's `{.x = v}` list: each value resolves here, in the scope
    // declaring the handle; each `.x` in the handle's type (U3).
    if (i->getInitializers().size()) {
        ast::ISymbolScope *type_s = traversedType(i, i->getName(), 0, false);
        for (std::vector<ast::IActionFieldInitializerUP>::const_iterator
                it=i->getInitializers().begin();
                it!=i->getInitializers().end(); it++) {
            resolveInitializer(type_s, it->get());
        }
    }
    checkMutableField(i);
    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
}

/**
 * PSS115 -- §4.7: "a triple-quoted string whose special elements reference only
 * constant expressions is itself constant". One that does not cannot appear
 * where a constant string is required.
 *
 * Reported at the point of *use*, not at the template: the same template text
 * is legal in an exec body and illegal in a `const` initializer, so the
 * template alone cannot say whether anything is wrong.
 */
void TaskResolveRefs::checkConstTemplate(
    ast::IExpr              *e,
    const ast::Location     &loc) {
    ast::IExprTemplateString *ts = dynamic_cast<ast::IExprTemplateString *>(e);

    if (ts && ts->getTemplate() && !ts->getTemplate()->getIs_const()) {
        m_ctxt->addErrorMarker(
            loc,
            "template string with non-constant elements is not a constant "
            "expression");
    }
}

/**
 * §9.1.6 b): `mutable` shall not be applied to a component field.
 *
 * A component instance is part of the system's immutable structure; whether
 * the fields *inside* it may change is decided by their own qualifiers, not by
 * the qualifier on the instance. This has to run after the field's type has
 * been resolved -- "is this type a component?" is not knowable from the
 * declaration alone.
 *
 * The other half of b), "nor to instance reference fields", is unreachable:
 * `mutable` and `instance` are alternatives of the same optional group in
 * `component_data_decl_qualifier`, so the two cannot both be written. Left
 * unimplemented deliberately rather than as an oversight -- cf. PSS103, which
 * was retired for the same reason.
 */
void TaskResolveRefs::checkMutableField(ast::IField *i) {
    if ((i->getAttr() & ast::FieldAttr::Mutable) == ast::FieldAttr::NoFlags) {
        return;
    }

    ast::IDataTypeUserDefined *ud =
        dynamic_cast<ast::IDataTypeUserDefined *>(i->getType());
    if (!ud || !ud->getType_id() || !ud->getType_id()->getTarget()) {
        return;
    }

    ast::IScopeChild *target_c =
        m_ctxt->resolveSymbolPathRef(ud->getType_id()->getTarget());
    if (!target_c) {
        return;
    }

    // Type references resolve to the wrapping symbol scope, not the
    // declaration -- the same indirection annotations hit in Phase 2.
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(target_c);
    if (ts && ts->getTarget()) {
        target_c = ts->getTarget();
    }

    if (dynamic_cast<ast::IComponent *>(target_c)) {
        m_ctxt->addErrorMarker(
            i->getName()->getLocation(),
            "illegal 'mutable' qualifier: not permitted on component field '%s'",
            i->getName()->getId().c_str());
    }
}

void TaskResolveRefs::visitFieldCompRef(ast::IFieldCompRef *i) {
    DEBUG_ENTER("visitFieldCompRef");
    DEBUG("Note: Skip during core symbol resolution");
    DEBUG_LEAVE("visitFieldCompRef");
}

void TaskResolveRefs::visitFunctionPrototype(ast::IFunctionPrototype *i) {
    DEBUG_ENTER("visitFunctionPrototype");

    if (i->getRtype()) {
        i->getRtype()->accept(m_this);
    }

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=i->getParameters().begin();
        it!=i->getParameters().end(); it++) {
        if ((*it)->getType()) {
            (*it)->getType()->accept(m_this);
        } else {
            // TODO: likely a category type
        }
        // A default value is an ordinary expression (F-N9: it was never
        // walked, so `int p = NOSUCH` was silent).
        if ((*it)->getDflt()) {
            (*it)->getDflt()->accept(m_this);
        }
    }
    DEBUG_LEAVE("visitFunctionPrototype");
} 

void TaskResolveRefs::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    DEBUG_ENTER("visitProceduralStmtRepeat %d", i->getSymtab().size());
    // The count is outside the loop: the index variable is not in scope in it
    // (F-N7: it was never walked).
    if (i->getCount()) {
        i->getCount()->accept(m_this);
    }
    pushProcScope(i);
    // `repeat (...) ;` -- an empty statement -- leaves body null.
    if (i->getBody()) {
        i->getBody()->accept(m_this);
    }
    popProcScope();
    DEBUG_LEAVE("visitProceduralStmtRepeat");
}

void TaskResolveRefs::typeForeachIterator(ast::IProceduralStmtForeach *i) {
    typeLoopIterator(i, i->getIt_id(), i->getPath());
}

void TaskResolveRefs::typeLoopIterator(
        ast::ISymbolScope       *loop,
        ast::IExprId            *it_id,
        ast::IExprRefPath       *coll_ref) {
    if (!it_id || !coll_ref || !coll_ref->getTarget()) {
        DEBUG("No iterator variable, or the collection did not resolve");
        return;
    }

    // The iterator variable registered on the loop node -- by the AST builder
    // for a procedural loop, by TaskBuildSymbolTree for an activity loop.
    std::unordered_map<std::string, int32_t>::const_iterator it =
        loop->getSymtab().find(it_id->getId());
    if (it == loop->getSymtab().end()
            || it->second < 0 || it->second >= (int32_t)loop->getChildren().size()) {
        return;
    }
    ast::IProceduralStmtDataDeclaration *var =
        dynamic_cast<ast::IProceduralStmtDataDeclaration *>(
            loop->getChildren().at(it->second).get());
    if (!var || var->getDatatype()) {
        return;
    }

    ast::IScopeChild *coll = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(),
        m_ctxt->root(),
        m_ctxt->inlineCtxt()).resolve(coll_ref->getTarget());

    ast::IDataType *elem_t = TaskGetCollectionElemType(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(coll);

    if (elem_t) {
        DEBUG("Iterator %s takes the collection's element type",
            it_id->getId().c_str());
        // Not owned: the type belongs to the collection's specialized
        // parameter list, which outlives the loop that borrows it.
        var->setDatatype(elem_t, false);
    }
}

void TaskResolveRefs::visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) {
    DEBUG_ENTER("visitProceduralStmtForeach %d", i->getSymtab().size());
    // Resolve the collection path in the OUTER scope (it must not see the
    // loop variables registered on the foreach node itself).
    if (i->getPath()) { i->getPath()->accept(m_this); }
    // The AST builder creates the iterator variable untyped -- at parse time
    // the collection is just a path. Give it the collection's element type now
    // that the path has resolved, so member access through the iterator
    // (`foreach (e : l) { e.field }`) has something to look `field` up in.
    typeForeachIterator(i);
    // Push the foreach scope so the iterator/index variables are visible while
    // resolving references in the body (e.g. `arr[i]`).
    pushProcScope(i);
    if (i->getBody()) { i->getBody()->accept(m_this); }
    popProcScope();
    DEBUG_LEAVE("visitProceduralStmtForeach");
}

// ---------------------------------------------------------------------------
// 4.7.1 -- template scopes
//
// The generated visitors are the wrong shape here. visitTemplateBlock calls
// visitTemplateElem first, which reaches visitSymbolScope -- pushing the scope,
// visiting its children and popping it again -- and only *then* walks the
// block's body. So the body would be resolved with the scope already popped,
// and a foreach iterator would be invisible inside its own block.
//
// These overrides push the scope around the body instead, which is what
// 4.7.1.2 asks for: the iterator, index and declared variables are "added to
// the scope until the block closing directive".
// ---------------------------------------------------------------------------

void TaskResolveRefs::visitTemplateString(ast::ITemplateString *i) {
    DEBUG_ENTER("visitTemplateString");
    m_ctxt->symtab()->pushScope(i);
    m_template_depth++;

    // Children are the synthesized declarations for `{% int x; %}`.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin(); it!=i->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }
    for (std::vector<ast::ITemplateElemUP>::const_iterator
        it=i->getElems().begin(); it!=i->getElems().end(); it++) {
        it->get()->accept(m_this);
    }

    m_template_depth--;
    m_ctxt->symtab()->popScope();

    // Only now: `is_const` and the scalar-type rule both ask what a reference
    // resolved to, so neither can be decided while the walk is still going.
    TaskTemplateCheck(m_ctxt).check(i);

    DEBUG_LEAVE("visitTemplateString");
}

void TaskResolveRefs::visitTemplateBlock(ast::ITemplateBlock *i) {
    DEBUG_ENTER("visitTemplateBlock");
    m_ctxt->symtab()->pushScope(i);

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin(); it!=i->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }
    for (std::vector<ast::ITemplateElemUP>::const_iterator
        it=i->getBody().begin(); it!=i->getBody().end(); it++) {
        it->get()->accept(m_this);
    }

    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitTemplateBlock");
}

void TaskResolveRefs::visitTemplateForeach(ast::ITemplateForeach *i) {
    DEBUG_ENTER("visitTemplateForeach");
    // The collection is resolved in the OUTER scope: it must not see the loop
    // variables this block introduces. Same rule as procedural foreach.
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    // getIt()/getIdx() are *declarations*, not references. Resolving them would
    // report the very names this block is introducing as unknown.
    visitTemplateBlock(i);
    DEBUG_LEAVE("visitTemplateForeach");
}

void TaskResolveRefs::visitTemplateRepeat(ast::ITemplateRepeat *i) {
    DEBUG_ENTER("visitTemplateRepeat");
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    visitTemplateBlock(i);
    DEBUG_LEAVE("visitTemplateRepeat");
}

void TaskResolveRefs::visitTemplateIfClause(ast::ITemplateIfClause *i) {
    DEBUG_ENTER("visitTemplateIfClause");
    // The guard belongs to the enclosing scope -- a variable declared inside
    // the clause body is not in scope for the condition that selects it.
    if (i->getCond()) {
        i->getCond()->accept(m_this);
    }
    visitTemplateBlock(i);
    DEBUG_LEAVE("visitTemplateIfClause");
}

void TaskResolveRefs::visitTemplateAssign(ast::ITemplateAssign *i) {
    DEBUG_ENTER("visitTemplateAssign");

    if (i->getRhs()) {
        i->getRhs()->accept(m_this);
    }

    // PSS112. 4.7.1.2 restricts `{% x = expr; %}` to a variable *previously
    // declared within the same triple-quoted string*; assigning to an action
    // attribute is illegal. Nothing about the syntax distinguishes the two, so
    // the only way to tell them apart is to ask which symtab the name came
    // from -- which is why template locals are real symbols in a real scope
    // rather than a side table.
    const std::string &name = i->getLhs()->getId()->getId();

    bool found = false;
    bool in_template = false;
    for (int32_t off=0; ; off++) {
        ast::ISymbolScope *scope = m_ctxt->symtab()->getScope(off);
        if (!scope) {
            break;
        }
        if (scope->getSymtab().find(name) != scope->getSymtab().end()) {
            found = true;
            in_template =
                dynamic_cast<ast::ITemplateString *>(scope) != 0 ||
                dynamic_cast<ast::ITemplateBlock *>(scope) != 0;
            break;
        }
    }

    if (!found) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getLhs()->getId()->getLocation(),
            "unknown identifier '%s'",
            name.c_str());
    } else if (!in_template) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getLhs()->getId()->getLocation(),
            "template assignment target '%s' is not declared within this "
            "template string",
            name.c_str());
    }

    DEBUG_LEAVE("visitTemplateAssign");
}

void TaskResolveRefs::visitMergedScopeChild(ast::IScopeChild *c) {
    // A member contributed by a type extension is walked here, in the scope
    // of the type it was merged into -- so the lexical chain a name inside it
    // is looked up along runs out through the *extended* type's package. LRM
    // 17.2 associates the extension with the package that encloses the
    // `extend` statement, and 17.2.3 applies that package's imports to the
    // body. Push it as a fallback for the duration of the visit; see
    // ResolveContext::pushExtensionCtxt and known-issues CL-N1.
    ast::ISymbolScope *decl_s = m_ctxt->extensionDeclScope(c);

    if (decl_s) {
        m_ctxt->pushExtensionCtxt(decl_s);
    }
    c->accept(m_this);
    if (decl_s) {
        m_ctxt->popExtensionCtxt();
    }
}

/**
 * `enum e : byte_t { ... }`. The declaration is reachable only through the
 * non-visiting `decl` back-pointer (see TaskBuildSymbolTree::visitEnumDecl),
 * so its base type was never resolved and `enum e : nosuch_t` was silent
 * (F-N4). It is written in the enclosing scope, so it is resolved before the
 * enum's own scope is pushed. Whether it is an integer type is CH07-39.
 */
void TaskResolveRefs::visitSymbolEnumScope(ast::ISymbolEnumScope *i) {
    DEBUG_ENTER("visitSymbolEnumScope %s", i->getName().c_str());
    if (i->getDecl() && i->getDecl()->getBase_type()) {
        i->getDecl()->getBase_type()->accept(m_this);
    }
    visitSymbolScope(i);
    DEBUG_LEAVE("visitSymbolEnumScope %s", i->getName().c_str());
}

/** A symbol's parameter types are written in the enclosing scope (4.4). */
void TaskResolveRefs::visitSymbolDeclaration(ast::ISymbolDeclaration *i) {
    DEBUG_ENTER("visitSymbolDeclaration %s", i->getName().c_str());
    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
            it=i->getParams().begin(); it!=i->getParams().end(); it++) {
        if ((*it)->getType()) {
            (*it)->getType()->accept(m_this);
        }
    }
    visitSymbolScope(i);
    DEBUG_LEAVE("visitSymbolDeclaration %s", i->getName().c_str());
}

/**
 * `s(a1, a2);` inlines symbol `s` (11.4). The name must be a symbol, and the
 * call must supply one argument per parameter -- a symbol parameter has no
 * default. Nothing visited the call before (S2), so `nosuch(a1);` linked.
 * The target is an ExprId, which has no slot for the binding (WS3.2), so it
 * is checked here and not recorded.
 */
void TaskResolveRefs::visitActivitySymbolCall(ast::IActivitySymbolCall *i) {
    DEBUG_ENTER("visitActivitySymbolCall");
    for (std::vector<ast::IExprUP>::const_iterator
            it=i->getParams().begin(); it!=i->getParams().end(); it++) {
        (*it)->accept(m_this);
    }

    ast::IExprRefName *rn = i->getTarget();
    ast::IExprId *id = rn ? rn->getId() : 0;
    if (!id) {
        DEBUG_LEAVE("visitActivitySymbolCall -- no target");
        return;
    }
    ast::IExprHierarchicalId *hid = m_ctxt->getFactory()->getAstFactory()->mkExprHierarchicalId();
    ast::IExprId *id_c = m_ctxt->getFactory()->getAstFactory()->mkExprId(
        id->getId(), id->getIs_escaped());
    id_c->setLocation(id->getLocation());
    hid->getElems().push_back(ast::IExprMemberPathElemUP(
        m_ctxt->getFactory()->getAstFactory()->mkExprMemberPathElem(id_c, 0)));
    ast::IExprRefPathContextUP ref(
        m_ctxt->getFactory()->getAstFactory()->mkExprRefPathContext(hid));
    ast::ISymbolRefPathUP target(TaskResolveRef(m_ctxt, true, false).resolve(ref.get()));
    ast::IScopeChild *target_c = target ? m_ctxt->resolveSymbolPathRef(target.get()) : 0;
    ast::ISymbolDeclaration *sym = dynamic_cast<ast::ISymbolDeclaration *>(target_c);

    if (!target_c) {
        m_ctxt->addErrorMarker(id->getLocation(),
            "unknown identifier '%s'", id->getId().c_str());
    } else if (!sym) {
        m_ctxt->addErrorMarker(id->getLocation(),
            "'%s' is not a symbol; only a symbol can be called in an activity",
            id->getId().c_str());
    } else {
        if (sym->getParams().size() != i->getParams().size()) {
            m_ctxt->addErrorMarker(id->getLocation(),
                "call to '%s' expects %d argument%s, got %d",
                id->getId().c_str(),
                (int)sym->getParams().size(),
                (sym->getParams().size() == 1) ? "" : "s",
                (int)i->getParams().size());
        }
        if (!rn->getTarget()) {
            rn->setTarget(target.release());
        }
    }
    DEBUG_LEAVE("visitActivitySymbolCall");
}

/**
 * `bind p { a.x, ... };` -- the pool path and the target paths are resolved
 * along component paths (WS4.5, U2), not by the ordinary lookup. Only the
 * action type named in a target is resolved here, as before WS3.2.
 */
void TaskResolveRefs::visitComponentBind(ast::IComponentBind *i) {
    for (std::vector<ast::IComponentBindTargetUP>::const_iterator
            it=i->getTargets().begin(); it!=i->getTargets().end(); it++) {
        if ((*it)->getType_id()) {
            (*it)->getType_id()->accept(m_this);
        }
    }
}

/**
 * An initializer is resolved by its handle or traversal, which knows the type
 * its path names a member of (resolveInitializer). Reached on its own only
 * where that type is unknown, so only the value is resolved.
 */
void TaskResolveRefs::visitActionFieldInitializer(ast::IActionFieldInitializer *i) {
    resolveInitializer(0, i);
}

/**
 * A handle declared in an activity (`A b {.x = 1};`): its type, then its
 * initializers, in the handle's type (U3).
 */
void TaskResolveRefs::visitActionHandleField(ast::IActionHandleField *i) {
    DEBUG_ENTER("visitActionHandleField");
    if (i->getType()) {
        i->getType()->accept(m_this);
    }
    if (i->getInitializers().size()) {
        ast::ISymbolScope *type_s = traversedType(i, i->getName(), 0, false);
        for (std::vector<ast::IActionFieldInitializerUP>::const_iterator
                it=i->getInitializers().begin();
                it!=i->getInitializers().end(); it++) {
            resolveInitializer(type_s, it->get());
        }
    }
    DEBUG_LEAVE("visitActionHandleField");
}

/**
 * `export target function f;` (20.4.2) names a function declared elsewhere.
 * It was never resolved, so an unknown name linked (F-N12). Only the binding
 * is checked here; "a static function with a native implementation" is a
 * semantic check.
 */
void TaskResolveRefs::visitExportFunction(ast::IExportFunction *i) {
    ast::IExprRefName *rn = i->getName();
    if (!rn || !rn->getId() || rn->getTarget()) {
        return;
    }
    ast::IExprId *id = rn->getId();
    ast::IExprHierarchicalId *hid = m_ctxt->getFactory()->getAstFactory()->mkExprHierarchicalId();
    ast::IExprId *id_c = m_ctxt->getFactory()->getAstFactory()->mkExprId(
        id->getId(), id->getIs_escaped());
    id_c->setLocation(id->getLocation());
    hid->getElems().push_back(ast::IExprMemberPathElemUP(
        m_ctxt->getFactory()->getAstFactory()->mkExprMemberPathElem(id_c, 0)));
    ast::IExprRefPathContextUP ref(
        m_ctxt->getFactory()->getAstFactory()->mkExprRefPathContext(hid));
    ast::ISymbolRefPathUP target(TaskResolveRef(m_ctxt, true, false).resolve(ref.get()));
    ast::IScopeChild *target_c = target ? m_ctxt->resolveSymbolPathRef(target.get()) : 0;

    if (!target_c) {
        m_ctxt->addErrorMarker(id->getLocation(),
            "unknown function '%s'", id->getId().c_str());
    } else if (!dynamic_cast<ast::ISymbolFunctionScope *>(target_c)) {
        m_ctxt->addErrorMarker(id->getLocation(),
            "'%s' is not a function", id->getId().c_str());
    } else {
        rn->setTarget(target.release());
    }
}

/** `instance a.b with T;` -- the instance path is U5; the type resolves here. */
void TaskResolveRefs::visitInstanceOverride(ast::IInstanceOverride *i) {
    if (i->getWith_t()) {
        i->getWith_t()->accept(m_this);
    }
}

void TaskResolveRefs::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
    m_ctxt->symtab()->pushScope(i);

    if (i->getImports()) {
        DEBUG_ENTER("  Resolve Imports");
        TaskResolveImports(m_ctxt).resolve(i);
        DEBUG_LEAVE("  Resolve Imports");
    }

    checkScopeAnnotations(i);

    DEBUG("Have %d children", i->getChildren().size());
    DEBUG_ENTER("visit children");
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        DEBUG_ENTER("visit child");
        visitMergedScopeChild(it->get());
        DEBUG_LEAVE("visit child");
    }
    DEBUG_LEAVE("visit children");

    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitSymbolScope %s", i->getName().c_str());
}

void TaskResolveRefs::visitSymbolExtendScope(ast::ISymbolExtendScope *i) {
    DEBUG_ENTER("visitSymbolExtendScope");
    DEBUG("Note: Skipping during core symbol resolution");

/*
    m_symtab_it->pushScope(i);

    for (std::vector<ast::IScopeChild *>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(this);
    }

    m_symtab_it->popScope();
 */

    DEBUG_LEAVE("visitSymbolExtendScope");
}

// void TaskResolveRefs::visitSymbolExecScope(ast::ISymbolExecScope *i) {
//     DEBUG_ENTER("visitSymbolExecScope \"%s\"", i->getName().c_str());
//     m_ctxt->symtab()->pushScope(i);

//     for (std::vector<ast::IScopeChildUP>::const_iterator
//         it=i->getChildren().begin();
//         it!=i->getChildren().end(); it++) {
//         (*it)->accept(this);
//     }

//     m_ctxt->symtab()->popScope();
//     DEBUG_LEAVE("visitSymbolExecScope \"%s\"", i->getName().c_str());
// }

void TaskResolveRefs::visitProceduralStmtExpr(ast::IProceduralStmtExpr *i) {
    // The one place a call is allowed to be void (LRM 20.5). Recorded rather
    // than checked here: by the time the ref-path is reached, the walk has no
    // way to ask what statement it is under.
    //
    // Saved and restored rather than assigned and cleared: a statement's own
    // expression can contain further calls -- `f(g())` -- and each of those
    // is an operand, not a statement.
    ast::IExpr *prev = m_stmt_expr;
    m_stmt_expr = i->getExpr();
    ast::VisitorBase::visitProceduralStmtExpr(i);
    m_stmt_expr = prev;
}

void TaskResolveRefs::checkVoidCallUse(
        ast::IExprMemberPathElem  *elem,
        ast::ISymbolFunctionScope *fn) {
    // LRM 20.5: "Functions not returning a value (declared with void return
    // type) may only be called as standalone procedural statements."
    //
    // The converse is explicitly *not* an error, and is not checked: "Calling
    // a nonvoid function as if it has no return value shall be legal, but it
    // is recommended to explicitly discard the return value by casting the
    // function call to void." A recommendation is not a rule.
    if (m_cur_refpath && m_cur_refpath == m_stmt_expr) {
        return;
    }

    // Any prototype with a return type is enough. A function is void only if
    // every declaration of it says so.
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=fn->getPrototypes().begin();
        it!=fn->getPrototypes().end(); it++) {
        if ((*it)->getRtype()) {
            return;
        }
    }

    m_ctxt->addMarker(
        MarkerSeverityE::Error,
        elem->getId()->getLocation(),
        "'%s' returns void, so its result cannot be used as a value",
        elem->getId()->getId().c_str());
}

void TaskResolveRefs::checkDeclarationConsistency(ast::ISymbolFunctionScope *i) {
    if (i->getPrototypes().size() < 2) {
        return;
    }

    // Compared against the *first* prototype rather than pairwise, because
    // that is the one every other pass already treats as authoritative:
    // visitFunctionDefinition inserts a definition's prototype at the front,
    // declaredTypeOf and TaskGetElemSymbolScope both take the first return
    // type they find, and m_func_s checks a `return` against front(). One
    // choice of authority, or the diagnostics disagree with each other.
    ast::IFunctionPrototype *base = i->getPrototypes().front();

    TaskCompareTypeRefs comp(m_ctxt->getFactory(), m_ctxt->root());

    for (uint32_t idx=1; idx<i->getPrototypes().size(); idx++) {
        ast::IFunctionPrototype *p = i->getPrototypes().at(idx);

        if (checkReturnTypeConsistency(base, p, comp)) {
            return;
        }
        if (checkParamListConsistency(base, p, comp)) {
            return;
        }
    }
}

bool TaskResolveRefs::checkReturnTypeConsistency(
        ast::IFunctionPrototype     *base,
        ast::IFunctionPrototype     *p,
        TaskCompareTypeRefs         &comp) {
    // `void` is not a data type in this AST -- it is the absence of one --
    // so it needs its own comparison, and it gets its own message. It is
    // also the only disagreement that can be stated with certainty
    // without resolving anything.
    if ((base->getRtype() == 0) != (p->getRtype() == 0)) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            p->getName()->getLocation(),
            "declarations of '%s' disagree about the return type: "
            "one returns void and the other does not",
            p->getName()->getId().c_str());
        return true;
    }

    if (!base->getRtype()) {
        return false;
    }

    // Only a *certain* difference is reported. `Unsure` covers a type
    // this parser cannot compare -- an unfolded width, an alias, a kind
    // with no comparison -- and every one of those is a case where the
    // two declarations may well agree. Under-reporting here costs a
    // missed diagnostic on invalid input; over-reporting rejects valid
    // input, which is worse.
    if (comp.compare(base->getRtype(), p->getRtype())
        == TaskCompareTypeRefs::Rel::NotEqual) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            p->getName()->getLocation(),
            "declarations of '%s' disagree about the return type",
            p->getName()->getId().c_str());
        return true;
    }

    return false;
}

/**
 * A parameter's direction as it *behaves*, rather than as it is written.
 *
 * LRM 20.2.1: the direction modifiers are optional, and an omitted one is
 * input. So `f(int a)` and `f(input int a)` are the same declaration written
 * two ways, and reporting them as a disagreement would reject valid code --
 * while `f(int a)` against `f(output int a)` is a real conflict and is
 * reported.
 *
 * Note that the *presence* of a modifier does carry a separate consequence --
 * it makes the function importable only (LRM 20.3.2) -- but that rule is
 * already applied across every prototype by
 * TaskBuildSymbolTree::checkNativeParamDir, so it does not need this one to
 * treat the two spellings as different.
 */
static ast::ParamDir effectiveDir(ast::IFunctionParamDecl *pd) {
    return (pd->getDir() == ast::ParamDir::ParamDir_Default)
        ? ast::ParamDir::ParamDir_In
        : pd->getDir();
}

/** How a parameter's position reads in a message: `parameter 2 ('len')`. */
static std::string paramDesc(uint32_t idx, ast::IFunctionParamDecl *pd) {
    char buf[32];
    snprintf(buf, sizeof(buf), "parameter %u", idx+1);
    std::string ret(buf);
    if (pd->getName()) {
        ret += " ('" + pd->getName()->getId() + "')";
    }
    return ret;
}

bool TaskResolveRefs::checkParamListConsistency(
        ast::IFunctionPrototype     *base,
        ast::IFunctionPrototype     *p,
        TaskCompareTypeRefs         &comp) {
    const std::string &fname = p->getName()->getId();
    ast::Location loc = p->getName()->getLocation();

    if (base->getParameters().size() != p->getParameters().size()) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            loc,
            "declarations of '%s' disagree about the number of parameters "
            "(%u and %u)",
            fname.c_str(),
            (uint32_t)base->getParameters().size(),
            (uint32_t)p->getParameters().size());
        return true;
    }

    for (uint32_t idx=0; idx<base->getParameters().size(); idx++) {
        ast::IFunctionParamDecl *b = base->getParameters().at(idx).get();
        ast::IFunctionParamDecl *q = p->getParameters().at(idx).get();

        // The kind separates a value parameter from a type parameter and from
        // each flavour of reference parameter -- `int a`, `type a`, `ref
        // action a`. These are not variations of one thing, so the comparison
        // below would be measuring types that are not comparable.
        if (b->getKind() != q->getKind()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error, loc,
                "declarations of '%s' disagree about what kind of %s is",
                fname.c_str(), paramDesc(idx, b).c_str());
            return true;
        }

        if (b->getIs_varargs() != q->getIs_varargs()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error, loc,
                "declarations of '%s' disagree about whether %s is varargs",
                fname.c_str(), paramDesc(idx, b).c_str());
            return true;
        }

        if (effectiveDir(b) != effectiveDir(q)) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error, loc,
                "declarations of '%s' disagree about the direction of %s",
                fname.c_str(), paramDesc(idx, b).c_str());
            return true;
        }

        // LRM 3.1 20.2.4 c: a default "may be specified in the redeclaration
        // ... but this value shall be equal" (3.0 forbade repeating it at
        // all, which is what this used to enforce -- F24). Only a *certain*
        // difference is reported: a value that does not fold is accepted.
        if (b->getDflt() && q->getDflt()
                && defaultsDiffer(b->getDflt(), q->getDflt())) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error, loc,
                "declarations of '%s' disagree about the default value of %s",
                fname.c_str(), paramDesc(idx, b).c_str());
            return true;
        }

        if (comp.compare(b->getType(), q->getType())
            == TaskCompareTypeRefs::Rel::NotEqual) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error, loc,
                "declarations of '%s' disagree about the type of %s",
                fname.c_str(), paramDesc(idx, b).c_str());
            return true;
        }
    }

    return false;
}

/**
 * True only when two default values certainly differ: both fold to integers
 * (TaskEvalExpr), or both are bool or string literals, and the values are not
 * equal. Anything else -- an enum item, an expression that does not fold -- is
 * "not known to differ".
 */
bool TaskResolveRefs::defaultsDiffer(ast::IExpr *a, ast::IExpr *b) {
    ast::IExprBool *ba = dynamic_cast<ast::IExprBool *>(a);
    ast::IExprBool *bb = dynamic_cast<ast::IExprBool *>(b);
    if (ba && bb) {
        return ba->getValue() != bb->getValue();
    }
    ast::IExprString *sa = dynamic_cast<ast::IExprString *>(a);
    ast::IExprString *sb = dynamic_cast<ast::IExprString *>(b);
    if (sa && sb) {
        return sa->getValue() != sb->getValue();
    }

    ast::ISymbolScope *root = dynamic_cast<ast::ISymbolScope *>(m_ctxt->root());
    TaskEvalExpr eval(m_ctxt->getFactory(), root);
    std::unique_ptr<IVal> va(eval.eval(a));
    std::unique_ptr<IVal> vb(eval.eval(b));
    IValInt *ia = dynamic_cast<IValInt *>(va.get());
    IValInt *ib = dynamic_cast<IValInt *>(vb.get());
    return ia && ib && ia->getValS() != ib->getValS();
}

void TaskResolveRefs::visitProceduralStmtReturn(ast::IProceduralStmtReturn *i) {
    // Resolve the returned expression first, whatever the verdict below: a
    // bad reference inside it should be reported on its own terms.
    ast::VisitorBase::visitProceduralStmtReturn(i);

    if (m_func_s.empty()) {
        // A `return` outside any function body. The grammar admits one in an
        // action's exec block, where there is nothing to check it against.
        DEBUG("Note: return outside a function body");
        return;
    }

    ast::IFunctionPrototype *proto = m_func_s.back();

    // A null return type is how `void` is spelled -- see
    // AstBuilderInt::mkFunctionPrototype, which leaves rtype at 0 unless the
    // return type parses as a data_type.
    bool is_void = (proto->getRtype() == 0);

    // Report at the statement, not at the function name: a body may hold
    // several returns and only one of them be wrong.
    ast::Location loc = i->getLocation();
    if (loc.lineno < 0) {
        loc = proto->getName()->getLocation();
    }

    if (is_void && i->getExpr()) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            loc,
            "'%s' returns void, so 'return' cannot take a value",
            proto->getName()->getId().c_str());
    } else if (!is_void && !i->getExpr()) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            loc,
            "'%s' has a return type, so 'return' must supply a value",
            proto->getName()->getId().c_str());
    }
}

void TaskResolveRefs::visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) {
    DEBUG_ENTER("visitSymbolFunctionScope %s (%d %p) ", 
    i->getName().c_str(),
    i->getPrototypes().size(),
    i->getBody());

    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=i->getPrototypes().begin();
        it!=i->getPrototypes().end(); it++) {
        (*it)->accept(m_this);
    }

    checkDeclarationConsistency(i);

//    if (i->getBody()) {
        DEBUG("Push function scope %s", i->getName().c_str());
        m_ctxt->symtab()->pushScope(i);
//        m_ctxt->symtab()->pushScope(i->getPlist());
//        DEBUG("Push function body scope");
//        m_ctxt->symtab()->pushScope(i->getBody());
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            (*it)->accept(m_this);
        }

        // Resolve references in the body
        if (i->getBody()) {
            DEBUG("--> visitBody");
            // Track which function's body this is, so that a `return` inside
            // it can be checked against the declared return type.
            // visitFunctionDefinition inserts the definition's own prototype
            // at the front, so front() is the one that carries this body.
            if (i->getPrototypes().size()) {
                m_func_s.push_back(i->getPrototypes().front());
            }
            i->getBody()->accept(m_this);
            if (i->getPrototypes().size()) {
                m_func_s.pop_back();
            }
            DEBUG("<-- visitBody");
        }

//        m_ctxt->symtab()->popScope();
        m_ctxt->symtab()->popScope();
//    }


    DEBUG_LEAVE("visitSymbolFunctionScope %s", i->getName().c_str());
}

// void TaskResolveRefs::visitSymbolStmtScope(ast::ISymbolStmtScope *i) {
//     DEBUG_ENTER("visitSymbolStmtScope %s", i->getName().c_str());
//     m_ctxt->symtab()->pushScope(i);
//     i->getTarget()->accept(m_this);
//     m_ctxt->symtab()->popScope();
//     DEBUG_LEAVE("visitSymbolStmtScope %s", i->getName().c_str());
// }

/**
 * True when ``dt`` is a bare reference to one of ``plist``'s own parameters.
 *
 * Such a reference resolves only inside the generic, so it must not be
 * resolved in the declaring scope -- where the name means nothing, or worse,
 * means some unrelated type that happens to share it.
 */
static bool namesTemplateParam(
        ast::ITemplateParamDeclList *plist,
        ast::IDataType              *dt) {
    ast::IDataTypeUserDefined *ud = dynamic_cast<ast::IDataTypeUserDefined *>(dt);
    if (!ud || !ud->getType_id() ||
        ud->getType_id()->getElems().size() != 1 ||
        !ud->getType_id()->getElems().at(0)->getId()) {
        return false;
    }
    const std::string &name = ud->getType_id()->getElems().at(0)->getId()->getId();
    for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
        it=plist->getParams().begin();
        it!=plist->getParams().end(); it++) {
        if ((*it)->getName() && (*it)->getName()->getId() == name) {
            return true;
        }
    }
    return false;
}

void TaskResolveRefs::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
    DEBUG_ENTER("visitSymbolTypeScope %s (param=%s specialized=%s)", 
        i->getName().c_str(),
        (i_ts->getParams())?"true":"false",
        (i_ts->getParams() && i_ts->getParams()->getSpecialized())?"true":"false");
    if (i_ts->getParams() && !i_ts->getParams()->getSpecialized()) {
        DEBUG("Note: Skipping symbol resolution in an unspecialized templated type");

        // One thing in an unspecialized generic's declaration must still be
        // resolved: the restriction on a category type parameter. It names a
        // concrete type in the *declaring* scope, and it has to be resolved
        // before any use of the generic, because checking an argument against
        // it happens while that use is being specialized -- which is to say,
        // before this type scope would otherwise be visited at all.
        //
        // Only restrictions. A parameter *default* may name an earlier
        // parameter of the same list (`struct S<type T, type U = T>`), which
        // does not resolve in the declaring scope; attempting it would report
        // an unknown type for a perfectly legal declaration.
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=i_ts->getParams()->getParams().begin();
            it!=i_ts->getParams()->getParams().end(); it++) {
            ast::ITemplateCategoryTypeParamDecl *cat =
                dynamic_cast<ast::ITemplateCategoryTypeParamDecl *>(it->get());
            if (!cat) {
                continue;
            }
            if (cat->getRestriction()) {
                DEBUG_ENTER("Resolve type-parameter restriction");
                cat->getRestriction()->accept(m_this);
                DEBUG_LEAVE("Resolve type-parameter restriction");
            }
            // A category parameter's default is checked against the
            // restriction the same way a supplied argument is, so it needs a
            // target too. The caveat above applies, so a default that spells
            // the name of a parameter in this same list is left alone.
            if (cat->getDflt() && !namesTemplateParam(i_ts->getParams(), cat->getDflt())) {
                DEBUG_ENTER("Resolve type-parameter default");
                cat->getDflt()->accept(m_this);
                DEBUG_LEAVE("Resolve type-parameter default");
            }
        }
    } else {
        ast::SymbolRefPathElemKind kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;

        if (i_ts->getParams() && i_ts->getParams()->getSpecialized()) {
            kind = ast::SymbolRefPathElemKind::ElemKind_TypeSpec;
            DEBUG("Processing specialization depth=%d", m_ctxt->specializationDepth());

            // TODO: need a way to detect that we have a superseding 
            // scope stack, so we don't redo it

            // Create a symbol-table iterator that:
            // - starts with m_root
            // - is preloaded with the scopes of the target type

            if (m_ctxt->specializationDepth() == 1) {
                DEBUG("Updating resolution stack to use local scope");
                m_ctxt->pushSymtab(TaskResolveSymbolPathRef(
                    m_ctxt->getDebugMgr(), m_ctxt->root()).mkIterator(
                        m_ctxt->getFactory()->mkAstSymbolTableIterator(m_ctxt->root()),
                        i));
            } else {
                DEBUG("Retaining existing resolution stack");
            }
            // TODO: need to resolve refs in the parameter list
            // relative to the containing type
            // Ensure parameter references are resolved
            DEBUG_ENTER("Resolve refs in parameter decl list");
            i_ts->getParams()->accept(m_this);
            DEBUG_LEAVE("Resolve refs in parameter decl list");
            if (m_ctxt->specializationDepth() == 1) {
                m_ctxt->popSymtab();
            }
        }

        // TODO: might need to defer this until after we've resolved
        // super-class
        m_ctxt->symtab()->pushScope(i, kind);

        // Resolve the super class (if any)
        if (dynamic_cast<ast::ITypeScope *>(i->getTarget())->getSuper_t()) {
            DEBUG("%s Has a super type ... resolving", i->getName().c_str());
            dynamic_cast<ast::ITypeScope *>(i->getTarget())->getSuper_t()->accept(this);
        } else {
            DEBUG("No super type");
        }

        if (i->getImports()) {
            DEBUG_ENTER("  Resolve Imports");
            TaskResolveImports(m_ctxt).resolve(i);
            DEBUG_LEAVE("  Resolve Imports");
        }

        checkScopeAnnotations(i);

        // Check on children. Through visitMergedScopeChild, because a type
        // scope is where extension-contributed members land.
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            if (!isActivityLabelAlias(i, it->get())) {
                visitMergedScopeChild(it->get());
            }
        }

        m_ctxt->symtab()->popScope();
    }
    DEBUG_LEAVE("visitSymbolTypeScope %s", i->getName().c_str());
}

namespace {

/**
 * An annotation initializer must be a constant expression (§7.13a).
 *
 * The grammar already restricts it to `constant_expression`, which rules out
 * calls and randomization but still admits a plain reference to an instance
 * field. Contextual references are exactly that case; package-qualified static
 * references name constants or enum items and are treated as constant.
 */
/**
 * Gathers the annotations owned by one symbol scope. Nested symbol scopes are
 * not descended into: each gets its own pass, under its own symbol-table scope.
 */
class AnnotationCollector : public ast::VisitorBase {
public:
    std::vector<ast::IAnnotation *> annotations;

    void collect(ast::IScope *s) {
        if (!s) {
            return;
        }
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin();
            it!=s->getChildren().end(); it++) {
            (*it)->accept(this);
        }
    }

    virtual void visitAnnotation(ast::IAnnotation *i) override {
        annotations.push_back(i);
    }

    virtual void visitSymbolScope(ast::ISymbolScope *i) override { }
    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override { }
    virtual void visitSymbolEnumScope(ast::ISymbolEnumScope *i) override { }
    virtual void visitSymbolExtendScope(ast::ISymbolExtendScope *i) override { }
    virtual void visitSymbolFunctionScope(ast::ISymbolFunctionScope *i) override { }
    virtual void visitSymbolChildrenScope(ast::ISymbolChildrenScope *i) override { }
};

class IsNonConstantExpr : public ast::VisitorBase {
public:
    bool non_constant = false;

    virtual void visitExprRefPathContext(ast::IExprRefPathContext *i) override {
        non_constant = true;
    }

    /**
     * A template nested inside a larger expression -- `"a" + """{{C}}"""`.
     * Its own `is_const` is the answer; descending would reach the references
     * inside the mustaches and call a perfectly constant template
     * non-constant.
     */
    virtual void visitExprTemplateString(ast::IExprTemplateString *i) override {
        if (!i->getTemplate() || !i->getTemplate()->getIs_const()) {
            non_constant = true;
        }
    }
};

std::string typeIdName(ast::ITypeIdentifier *type_id) {
    std::string ret;
    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
        it=type_id->getElems().begin();
        it!=type_id->getElems().end(); it++) {
        if (ret.size()) {
            ret += "::";
        }
        ret += (*it)->getId()->getId();
    }
    return ret;
}

}

void TaskResolveRefs::checkScopeAnnotations(ast::ISymbolScope *scope) {
    AnnotationCollector collector;
    collector.collect(dynamic_cast<ast::IScope *>(scope));

    // An annotation on the declaration itself hangs off the wrapped AST node.
    // Its type is resolved from inside the declaration's scope rather than the
    // enclosing one; annotation types are package-scope only (§7.13b), so the
    // outward lookup reaches the same declaration either way.
    if (scope->getTarget()) {
        collector.collect(dynamic_cast<ast::IScope *>(scope->getTarget()));
        for (std::vector<ast::IAnnotationUP>::const_iterator
            it=scope->getTarget()->getAnnotations().begin();
            it!=scope->getTarget()->getAnnotations().end(); it++) {
            collector.annotations.push_back(it->get());
        }
    }

    for (std::vector<ast::IAnnotation *>::const_iterator
        it=collector.annotations.begin();
        it!=collector.annotations.end(); it++) {
        if (m_checked_annotations.insert(*it).second) {
            (*it)->accept(m_this);
        }
    }
}

void TaskResolveRefs::visitAnnotation(ast::IAnnotation *i) {
    DEBUG_ENTER("visitAnnotation");
    ast::ITypeIdentifier *type_id = i->getType();
    if (!type_id) {
        DEBUG_LEAVE("visitAnnotation (no type)");
        return;
    }

    std::string type_name = typeIdName(type_id);

    if (!type_id->getTarget()) {
        // Resolve the annotation type ahead of the generic traversal, quietly:
        // TaskResolveRef reports an unresolved type identifier as an error, and
        // an unknown annotation type must not fail the build.
        type_id->setTarget(
            TaskResolveRef(m_ctxt, true, false).resolve(type_id));
    }

    if (!type_id->getTarget()) {
        // §7.13: "PSS processing tools shall disregard unrecognized
        // annotations". Deliberately not routed through the normal
        // unresolved-type error path: an unknown annotation type must never
        // fail the build, and nothing inside it is checked further.
        // The standard annotations (@doc, @code_doc) live in std_pkg and are
        // as import-dependent as any other core-library name, so say which
        // import is missing rather than implying the annotation is unknown.
        std::string core_pkg = findCoreLibraryPackage(
            dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()), type_name);

        if (!core_pkg.empty()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Warn,
                i->getLocation(),
                "unknown annotation type '%s'; declared in %s -- add "
                "'import %s::*;'. Annotation disregarded",
                type_name.c_str(),
                core_pkg.c_str(),
                core_pkg.c_str());
        } else {
            m_ctxt->addMarker(
                MarkerSeverityE::Warn,
                i->getLocation(),
                "unknown annotation type '%s'; annotation disregarded",
                type_name.c_str());
        }
        DEBUG_LEAVE("visitAnnotation (unresolved)");
        return;
    }

    // Only now visit the parameters: nothing inside an unrecognized annotation
    // is checked, so an unknown annotation contributes no diagnostics beyond
    // the one warning above.
    VisitorBase::visitAnnotation(i);

    ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(type_id->getTarget());
    ast::ISymbolScope *decl_s = dynamic_cast<ast::ISymbolScope *>(target_c);

    for (std::vector<ast::IAnnotationParamUP>::const_iterator
        it=i->getParameters().begin();
        it!=i->getParameters().end(); it++) {
        ast::IAnnotationParam *param = it->get();

        if (!param->getName()) {
            continue;
        }
        const std::string &name = param->getName()->getId()->getId();

        // Use TaskFindPathElem rather than the scope's own symtab: fields
        // contributed by `extend annotation` are not merged into the symbol
        // scope's children, and a plain symtab lookup would report them as
        // unknown.
        TaskFindPathElem::Result res = {0, -1, -1};
        if (decl_s) {
            res = TaskFindPathElem(
                m_ctxt->getDebugMgr(),
                m_ctxt->root()).find(decl_s, param->getName()->getId());
        }

        if (decl_s && !res.sym) {
            m_ctxt->addErrorMarker(
                param->getLocation(),
                "unknown identifier '%s' in annotation type '%s'",
                name.c_str(),
                type_name.c_str());
            continue;
        }

        // Record the binding (WS3.2): the annotation type's path, a Super
        // step per base type crossed, then the member. `super_idx` is the
        // number of hops -- 0 for the type's own member. One Super too many
        // left every such binding pointing past the root of the hierarchy,
        // at nothing (found by refcov's dead-path check).
        if (res.sym && res.idx >= 0 && !param->getName()->getTarget()) {
            ast::ISymbolRefPath *ref =
                m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
            ref->getPath() = type_id->getTarget()->getPath();
            for (int32_t s=0; s<res.super_idx; s++) {
                ref->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_Super, 0});
            }
            ref->getPath().push_back({ast::SymbolRefPathElemKind::ElemKind_ChildIdx, res.idx});
            param->getName()->setTarget(ref);
        }

        if (param->getValue()) {
            // A template initializer answers the constant question itself
            // (PSS115) and is not put through the crude walker below, which
            // would see the references *inside* the mustaches and report a
            // constant template as non-constant.
            if (dynamic_cast<ast::IExprTemplateString *>(param->getValue())) {
                checkConstTemplate(param->getValue(), param->getLocation());
                continue;
            }

            IsNonConstantExpr chk;
            param->getValue()->accept(&chk);
            if (chk.non_constant) {
                m_ctxt->addErrorMarker(
                    param->getLocation(),
                    "annotation initializer for '%s' is not a constant expression",
                    name.c_str());
            }
        }
    }

    DEBUG_LEAVE("visitAnnotation");
}

void TaskResolveRefs::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    DEBUG_ENTER("visitDataTypeUserDefined");
    if (i->getType_id()->getTarget()) {
        DEBUG("Symbol already resolved");
        DEBUG_LEAVE("visitDataTypeUserDefined");
        return;
    }
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i->getType_id());

    if (target) {
        DEBUG("Success");
        i->getType_id()->setTarget(target);

        // Guarded: a resolved *path* is not the same as a reachable node. An
        // override's path is built before super types are resolved, so its
        // final step can index past the end of the scope it names and come
        // back null -- `override action base_a` seen from a sibling subtype is
        // the case that crashed here. addRef only records a file-to-file edge
        // for the include graph, so skipping it costs nothing but the edge.
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        if (target_c) {
            m_ctxt->addRef(
                i->getLocation().fileid,
                target_c->getLocation().fileid);
        }
    } else {
        DEBUG("Failed");
        // char tmp[1024];
        // sprintf(tmp, "failed to find user-defined datatype");
        // IMarkerUP marker(m_factory->mkMarker(
        //     tmp,
        //     MarkerSeverityE::Error,
        //     i->getLocation()
        // ));
        // m_marker_l->marker(marker.get());
    }

    DEBUG_LEAVE("visitDataTypeUserDefined");
}


/**
 * Resolve an exec block tag's struct type (20.5.4), exactly once per node.
 */
// `e_t in [A, ..B]`: a domain is an expected-type context (8.4.3), so a bare
// name there is first an item of e_t, whatever is lexically visible -- an
// enum reached through `pkg::e_t` has no items in scope. Anything else, and a
// name that is not an item, resolves as usual.
void TaskResolveRefs::visitDataTypeEnum(ast::IDataTypeEnum *i) {
    DEBUG_ENTER("visitDataTypeEnum");
    if (i->getTid()) {
        i->getTid()->accept(m_this);
    }

    ast::IExprDomainOpenRangeList *dom = i->getIn_rangelist();
    if (!dom) {
        DEBUG_LEAVE("visitDataTypeEnum -- no domain");
        return;
    }

    ast::ISymbolRefPath *enum_p = (i->getTid() && i->getTid()->getType_id())
        ? i->getTid()->getType_id()->getTarget() : 0;
    ast::ISymbolEnumScope *enum_s = enum_p
        ? dynamic_cast<ast::ISymbolEnumScope *>(m_ctxt->resolveSymbolPathRef(enum_p))
        : 0;

    auto bind_item = [&](ast::IExpr *e) {
        ast::IExprRefPathContext *rp = dynamic_cast<ast::IExprRefPathContext *>(e);
        if (enum_s && rp && !rp->getTarget() && !rp->getIs_super()
                && rp->getHier_id()->getElems().size() == 1
                && !rp->getHier_id()->getElems().at(0)->getSubscript().size()
                && !rp->getHier_id()->getElems().at(0)->getParams()) {
            auto it = enum_s->getSymtab().find(
                rp->getHier_id()->getElems().at(0)->getId()->getId());
            if (it != enum_s->getSymtab().end()) {
                ast::ISymbolRefPath *ref =
                    m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
                ref->getPath() = enum_p->getPath();
                ref->getPath().push_back({
                    ast::SymbolRefPathElemKind::ElemKind_ChildIdx, it->second});
                rp->setTarget(ref);
            }
        }
        e->accept(m_this);
    };

    for (std::vector<ast::IExprDomainOpenRangeValueUP>::const_iterator
            it=dom->getValues().begin();
            it!=dom->getValues().end(); it++) {
        if ((*it)->getLhs()) bind_item((*it)->getLhs());
        if ((*it)->getRhs()) bind_item((*it)->getRhs());
    }
    DEBUG_LEAVE("visitDataTypeEnum");
}

// `"a,b".split(",").size()`: the receiver is a literal, so its type is known
// from its form. A string member is checked against the `string` pseudo-type's
// prototypes, as a call on a string field is; a collection member is only
// name-checked (P3-X6d). Once a member's result type is not known here, the
// rest of the chain is left unchecked rather than guessed at.
void TaskResolveRefs::visitExprMemberCall(ast::IExprMemberCall *i) {
    DEBUG_ENTER("visitExprMemberCall");
    enum class Kind { String, Collection, Unknown };

    if (i->getReceiver()) {
        i->getReceiver()->accept(m_this);
    }

    Kind kind = Kind::Unknown;
    if (dynamic_cast<ast::IExprString *>(i->getReceiver())
            || dynamic_cast<ast::IExprTemplateString *>(i->getReceiver())) {
        kind = Kind::String;
    } else if (dynamic_cast<ast::IExprAggrLiteral *>(i->getReceiver())) {
        kind = Kind::Collection;
    }

    for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
            it=i->getMembers().begin();
            it!=i->getMembers().end(); it++) {
        ast::IExprMemberPathElem *elem = it->get();
        const std::string &name = elem->getId()->getId();

        if (elem->getParams()) {
            for (auto p=elem->getParams()->getParameters().begin();
                    p!=elem->getParams()->getParameters().end(); p++) {
                (*p)->accept(m_this);
            }
        }
        for (auto s=elem->getSubscript().begin(); s!=elem->getSubscript().end(); s++) {
            (*s)->accept(m_this);
        }

        if (kind == Kind::Unknown) {
            continue;
        }

        ast::IScopeChild *proto = 0;
        bool found;
        if (kind == Kind::String) {
            ast::ISymbolScope *string_s = builtinStringScope_rr(m_ctxt->root());
            if (string_s) {
                proto = TaskFindPathElem(
                    m_ctxt->getDebugMgr(),
                    m_ctxt->root()).find(string_s, elem->getId()).sym;
            }
            found = string_s ? (proto != 0)
                : (stringMethods().find(name) != stringMethods().end());
        } else {
            found = (collectionMethods().find(name) != collectionMethods().end());
        }

        if (!found) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "unknown method '%s' on %s",
                name.c_str(),
                (kind == Kind::String) ? "string" : "built-in type");
            break;
        }
        if (!elem->getParams()) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "'%s' is a method; call it as '%s()'",
                name.c_str(), name.c_str());
            break;
        }

        elem->setTarget(-2);    // resolved, not to a child index (as for fields)

        // The next member applies to this one's result.
        kind = Kind::Unknown;
        if (proto) {
            TaskCheckCallArgs(m_ctxt).check(proto, elem);
            ast::ISymbolFunctionScope *fs = dynamic_cast<ast::ISymbolFunctionScope *>(proto);
            ast::IFunctionPrototype *fp = (fs && fs->getPrototypes().size())
                ? fs->getPrototypes().at(0) : 0;
            ast::IDataType *rt = fp ? fp->getRtype() : 0;
            if (dynamic_cast<ast::IDataTypeString *>(rt)) {
                kind = Kind::String;
            } else if (dynamic_cast<ast::IDataTypeUserDefined *>(rt)) {
                // BuiltinsFactory spells its results list<...> this way.
                kind = Kind::Collection;
            }
        }
        if (elem->getSubscript().size()) {
            kind = Kind::Unknown;
        }
    }
    DEBUG_LEAVE("visitExprMemberCall");
}

/**
 * `import [plat] [lang] function f;` -- LRM 20.4.1, Syntax 95 a: the function
 * is declared separately, and this attaches an import to it. The name is bound
 * like any type identifier, but must name a function, and the import obeys the
 * same one-import, not-also-defined rules as the prototype form
 * (TaskBuildSymbolTree::visitFunctionImportProto).
 */
void TaskResolveRefs::visitFunctionImportType(ast::IFunctionImportType *i) {
    DEBUG_ENTER("visitFunctionImportType");
    ast::ITypeIdentifier *tid = i->getType();
    if (!tid || !tid->getElems().size()) {
        DEBUG_LEAVE("visitFunctionImportType -- no name");
        return;
    }
    const ast::Location &loc = tid->getElems().back()->getId()->getLocation();
    std::string name = tid->getElems().back()->getId()->getId();

    if (!tid->getTarget()) {
        tid->setTarget(TaskResolveRef(m_ctxt, true, false).resolve(tid));
    }
    ast::IScopeChild *target = tid->getTarget()
        ? m_ctxt->resolveSymbolPathRef(tid->getTarget()) : 0;
    ast::ISymbolFunctionScope *func = dynamic_cast<ast::ISymbolFunctionScope *>(target);

    if (!target) {
        m_ctxt->addErrorMarker(loc,
            "unknown function '%s': an import of this form needs a separate "
            "declaration of the function (20.4.1)", name.c_str());
    } else if (!func) {
        m_ctxt->addErrorMarker(loc, "'%s' is not a function", name.c_str());
    } else if (func->getBody()) {
        m_ctxt->addErrorMarker(loc,
            "function '%s' cannot be both defined and imported", name.c_str());
    } else if (func->getImport_specs().size()) {
        m_ctxt->addErrorMarker(loc,
            "function '%s' is already imported", name.c_str());
    } else {
        func->getImport_specs().push_back(ast::IFunctionImportUP(
            m_ctxt->getFactory()->getAstFactory()->mkFunctionImport(
                i->getPlat(), i->getLang())));
        for (std::vector<ast::IFunctionPrototype *>::const_iterator
                it=func->getPrototypes().begin();
                it!=func->getPrototypes().end(); it++) {
            if (i->getPlat() == ast::PlatQual::PlatQual_Solve) {
                (*it)->setIs_solve(true);
            } else if (i->getPlat() == ast::PlatQual::PlatQual_Target) {
                (*it)->setIs_target(true);
            }
        }
    }
    DEBUG_LEAVE("visitFunctionImportType");
}

void TaskResolveRefs::visitExecBlockTag(ast::IExecBlockTag *i) {
    DEBUG_ENTER("visitExecBlockTag");
    if (!m_checked_exec_tags.insert(i).second) {
        DEBUG_LEAVE("visitExecBlockTag -- already checked");
        return;
    }
    if (i->getType()) {
        i->getType()->accept(m_this);
    }
    if (i->getLiteral()) {
        i->getLiteral()->accept(m_this);
    }
    DEBUG_LEAVE("visitExecBlockTag");
}

void TaskResolveRefs::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    DEBUG_ENTER("visitTypeIdentifier %s", i->getElems().at(0)->getId()->getId().c_str());

    // If this reference is already resolved, leave it alone. This node may have
    // been resolved in its proper instantiation context and then copied into a
    // freshly-created template specialization (see TaskGetSpecializedTemplateType).
    // Re-resolving here would use the specialization's declaration scope, which
    // does not include the instantiation site -- so a package-local type argument
    // (e.g. an array element type) would spuriously fail and clobber the good
    // target with a null. Mirror visitDataTypeUserDefined, which guards likewise.
    if (i->getTarget()) {
        DEBUG("Symbol already resolved");
        DEBUG_LEAVE("visitTypeIdentifier");
        return;
    }

    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i);

    if (target) {
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getElems().front()->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }
    i->setTarget(target);
    DEBUG_LEAVE("visitTypeIdentifier");
}

void TaskResolveRefs::visitStruct(ast::IStruct *i) {
    DEBUG_ENTER("visitStruct");
    VisitorBase::visitStruct(i);
    DEBUG_LEAVE("visitStruct");
}

void TaskResolveRefs::visitGenericConstraintDeclBool(ast::IGenericConstraintDeclBool *i) {
    DEBUG_ENTER("visitGenericConstraintDeclBool");

    // Register parameter names so they are not flagged as unknown. Their
    // types are resolved in the enclosing scope (F14, minimal fix); binding
    // the names themselves needs a parameter scope (WS8.7).
    std::set<std::string> saved = m_generic_constraint_params;
    for (auto &p : i->getParameters()) {
        if (p->getType()) {
            p->getType()->accept(m_this);
        }
        if (p->getName()) {
            m_generic_constraint_params.insert(p->getName()->getId());
        }
    }

    // Visit constraint body
    visitConstraintBlock(i);

    m_generic_constraint_params = saved;
    DEBUG_LEAVE("visitGenericConstraintDeclBool");
}

void TaskResolveRefs::visitGenericConstraintDeclValue(ast::IGenericConstraintDeclValue *i) {
    DEBUG_ENTER("visitGenericConstraintDeclValue");

    // `constraint T f(...) expr;` -- T is written in the enclosing scope. It
    // was never walked, so an unknown T reached only the completeness gate.
    if (i->getReturn_type()) {
        i->getReturn_type()->accept(m_this);
    }

    std::set<std::string> saved = m_generic_constraint_params;
    for (auto &p : i->getParameters()) {
        if (p->getType()) {
            p->getType()->accept(m_this);     // see visitGenericConstraintDeclBool
        }
        if (p->getName()) {
            m_generic_constraint_params.insert(p->getName()->getId());
        }
    }

    // Visit the return expression
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }

    m_generic_constraint_params = saved;
    DEBUG_LEAVE("visitGenericConstraintDeclValue");
}

bool TaskResolveRefs::isGenericConstraintParam(const std::string &name) const {
    return m_generic_constraint_params.find(name) != m_generic_constraint_params.end();
}

dmgr::IDebug *TaskResolveRefs::m_dbg = 0;


// --- PSS 3.1 §21.14.1: field names in a masked register write --------------
//
// `regs.csr.write_field("ch_en", 1)` names a declared field of the register's
// value type. The string spelling is forced by the LRM's own signature --
// `write_field(string name, bit[SZ] val)` -- and is not a sign that the name is
// data: §21.14.1 restricts it to a string *literal* precisely so a tool can
// resolve it at compile time.
//
// Resolving it is name binding, which is this pass's job. Everything the parser
// resolves elsewhere -- types, members, methods, enum items -- goes through
// here, and a name that did not would be resolved instead by each consumer, or
// by none. Before this, `write_field("chan_en", 1)` -- one letter wrong --
// linked clean and wrote a register bit nobody asked for.
//
// What is NOT decided here: which bits a resolved field occupies. `packed_s<>`
// layout is a target representation -- the C and SystemVerilog backends order
// it oppositely, on purpose -- so it belongs to the compiler, which folds the
// mask. This pass answers "which field", and the compiler answers "which bits".

bool TaskResolveRefs::regValueStruct(
        ast::ISymbolScope  *recv_s,
        ast::IStruct      **vs) {
    *vs = 0;
    ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(recv_s);

    // Bounded rather than "until the super is null": a super chain is a handful
    // of links, and a cycle here would hang the parse instead of diagnosing it.
    for (int32_t depth=0; ts && depth<32; depth++) {
        ast::ITypeScope *decl = dynamic_cast<ast::ITypeScope *>(ts->getTarget());

        if (!decl) {
            return false;
        }

        ast::ITemplateParamDeclList *params = decl->getParams();

        if (params) {
            for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
                it=params->getParams().begin();
                it!=params->getParams().end(); it++) {
                if (!(*it)->getName() || (*it)->getName()->getId() != "R") {
                    continue;
                }

                // This is reg_c. Its bound R is carried as the parameter's
                // *default*: TaskGetSpecializedTemplateType copies the
                // declaration and replaces the parameter list with the bound
                // one, so a specialization's default IS its argument.
                ast::ITemplateGenericTypeParamDecl *tp =
                    dynamic_cast<ast::ITemplateGenericTypeParamDecl *>(it->get());

                if (!tp || !tp->getDflt()) {
                    // The unspecialized declaration: nothing is bound, so
                    // there is nothing to resolve against.
                    return false;
                }

                ast::IDataTypeUserDefined *udt =
                    dynamic_cast<ast::IDataTypeUserDefined *>(tp->getDflt());

                if (!udt || !udt->getType_id()) {
                    // reg_c<bit[32]>: a register, but with no named fields.
                    // Reported by the caller, which knows what was asked for.
                    return true;
                }

                ast::ISymbolTypeScope *sts = TaskResolveSymbolPathRef(
                        m_ctxt->getDebugMgr(), m_ctxt->root())
                    .resolveT<ast::ISymbolTypeScope>(
                        udt->getType_id()->getTarget());
                *vs = sts
                    ? dynamic_cast<ast::IStruct *>(sts->getTarget())
                    : 0;
                return true;
            }
        }

        // Not reg_c itself. A named register type --
        // `pure component csr_r : reg_c<csr_s, ...>` -- puts exactly one link
        // between the field's type and the register; an inline
        // `reg_c<csr_s, ...> csr;` puts none.
        if (!decl->getSuper_t()) {
            return false;
        }

        // TaskResolveSymbolPathRef, not a bare path walk: the super of a named
        // register type is a *specialization* (`reg_c<csr_s,?,32>`), which
        // lives in the base type's spec_types rather than among its children,
        // so the plain index walk cannot reach it and silently yields null.
        ts = TaskResolveSymbolPathRef(
                m_ctxt->getDebugMgr(), m_ctxt->root())
            .resolveT<ast::ISymbolTypeScope>(decl->getSuper_t()->getTarget());
    }

    return false;
}

/// The declared field of `vs` named `n`, or null.
static ast::IField *findRegField(ast::IStruct *vs, const std::string &n) {
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=vs->getChildren().begin(); it!=vs->getChildren().end(); it++) {
        ast::IField *f = dynamic_cast<ast::IField *>(it->get());
        if (f && f->getName() && f->getName()->getId() == n) {
            return f;
        }
    }
    return 0;
}

/// The closest declared field name to `n`, for a `did you mean` suggestion.
static std::string closestRegField(ast::IStruct *vs, const std::string &n) {
    std::string best;
    int bestDist = 3;
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=vs->getChildren().begin(); it!=vs->getChildren().end(); it++) {
        ast::IField *f = dynamic_cast<ast::IField *>(it->get());
        if (!f || !f->getName()) {
            continue;
        }
        int d = editDistance_rr(n, f->getName()->getId());
        if (d > 0 && d < bestDist) {
            bestDist = d;
            best = f->getName()->getId();
        }
    }
    return best;
}

static const char *structName(ast::IStruct *vs) {
    return (vs->getName())?vs->getName()->getId().c_str():"<anonymous>";
}

ast::IField *TaskResolveRefs::resolveRegField(
        ast::IExprMemberPathElem *elem,
        ast::IStruct             *vs,
        ast::IExpr               *name_e) {
    const std::string &method = elem->getId()->getId();

    ast::IExprString *lit = dynamic_cast<ast::IExprString *>(name_e);

    if (!lit) {
        // §21.14.1(a). Reported here rather than left to the compiler because
        // this is the restriction that makes compile-time resolution possible
        // at all, and "must be a string literal" is a better answer than
        // whatever the compiler would say about a mask it could not fold.
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "%s: the field name must be a string literal (PSS 3.1 21.14.1); "
            "it names a declared field of '%s' and is resolved at compile time",
            method.c_str(),
            structName(vs));
        return 0;
    }

    const std::string &n = lit->getValue();

    if (n.find('.') != std::string::npos) {
        // §21.14.1(b): top-level fields only.
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "%s: field name '%s' must not be a hierarchical reference "
            "(PSS 3.1 21.14.1)",
            method.c_str(),
            n.c_str());
        return 0;
    }

    ast::IField *f = findRegField(vs, n);

    if (!f) {
        std::string suggestion = closestRegField(vs, n);
        if (suggestion.empty()) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "no field '%s' in register value type '%s'",
                n.c_str(),
                structName(vs));
        } else {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "no field '%s' in register value type '%s'; did you mean '%s'?",
                n.c_str(),
                structName(vs),
                suggestion.c_str());
        }
        return 0;
    }

    if (catOfDataType(f->getType()) == TypeCat::Aggregate) {
        // §21.14.1(c): the value written is a bit vector, so a field that is
        // not one cannot receive it.
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "%s: field '%s' of '%s' has a composite type; field-wise register "
            "access applies to scalar fields only (PSS 3.1 21.14.1)",
            method.c_str(),
            n.c_str(),
            structName(vs));
        return 0;
    }

    return f;
}

void TaskResolveRefs::checkRegFieldRefs(
        ast::IExprMemberPathElem *elem,
        ast::ISymbolScope        *recv_s) {
    if (!elem->getParams()) {
        return;
    }

    const std::string &method = elem->getId()->getId();
    bool one    = (method == "write_field");
    bool many   = (method == "write_fields");
    bool masked = (method == "write_masked");

    if (!one && !many && !masked) {
        return;
    }

    ast::IStruct *vs = 0;

    if (!regValueStruct(recv_s, &vs)) {
        // Not a register. A user type is free to have a method of this name,
        // and judging it here would be a false positive on someone else's API.
        return;
    }

    if (!vs) {
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "%s: this register's value type is not a struct, so it has no "
            "named fields (PSS 3.1 21.14.1)",
            method.c_str());
        return;
    }

    const std::vector<ast::IExprUP> &args = elem->getParams()->getParameters();

    if (one) {
        if (args.size() >= 1) {
            resolveRegField(elem, vs, args.at(0).get());
        }
        return;
    }

    if (many) {
        if (args.size() < 2) {
            // Arity is checkCallArity's to report; nothing to resolve.
            return;
        }

        ast::IExprAggrList *names =
            dynamic_cast<ast::IExprAggrList *>(args.at(0).get());
        ast::IExprAggrList *vals =
            dynamic_cast<ast::IExprAggrList *>(args.at(1).get());

        if (!names) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "write_fields: the field names must be a list literal of "
                "string literals; a runtime list cannot be resolved at compile "
                "time (PSS 3.1 21.14.1)");
            return;
        }

        if (vals && names->getElems().size() != vals->getElems().size()) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "write_fields: %d field name(s) but %d value(s)",
                (int32_t)names->getElems().size(),
                (int32_t)vals->getElems().size());
        }

        std::set<std::string> seen;

        for (std::vector<ast::IExprUP>::const_iterator
            it=names->getElems().begin(); it!=names->getElems().end(); it++) {
            ast::IField *f = resolveRegField(elem, vs, it->get());
            if (!f) {
                continue;
            }
            // §21.14.1(d). It matters more here than it looks: the whole point
            // of the plural form is that the fields are written in ONE
            // read-modify-write, so naming a field twice does not write it
            // twice -- one of the two values is simply lost.
            if (!seen.insert(f->getName()->getId()).second) {
                m_ctxt->addErrorMarker(
                    elem->getId()->getLocation(),
                    "write_fields: duplicate field name '%s' (PSS 3.1 21.14.1)",
                    f->getName()->getId().c_str());
            }
        }
        return;
    }

    // write_masked(R mask, R val): the arguments are values of the register's
    // own type, so a struct literal names its fields directly. A non-literal
    // argument is a whole value and has nothing to check.
    for (uint32_t ai=0; ai<args.size() && ai<2; ai++) {
        ast::IExprAggrStruct *sl =
            dynamic_cast<ast::IExprAggrStruct *>(args.at(ai).get());

        if (!sl) {
            continue;
        }

        std::set<std::string> seen;

        for (std::vector<ast::IExprAggrStructElemUP>::const_iterator
            it=sl->getElems().begin(); it!=sl->getElems().end(); it++) {
            if (!(*it)->getName()) {
                continue;
            }

            const std::string &n = (*it)->getName()->getId()->getId();

            if (!findRegField(vs, n)) {
                std::string suggestion = closestRegField(vs, n);
                if (suggestion.empty()) {
                    m_ctxt->addErrorMarker(
                        elem->getId()->getLocation(),
                        "write_masked: no field '%s' in register value type '%s'",
                        n.c_str(), structName(vs));
                } else {
                    m_ctxt->addErrorMarker(
                        elem->getId()->getLocation(),
                        "write_masked: no field '%s' in register value type "
                        "'%s'; did you mean '%s'?",
                        n.c_str(), structName(vs), suggestion.c_str());
                }
                continue;
            }

            if (!seen.insert(n).second) {
                m_ctxt->addErrorMarker(
                    elem->getId()->getLocation(),
                    "write_masked: duplicate field '%s' in the %s literal",
                    n.c_str(), (ai==0)?"mask":"value");
            }
        }
    }
}


}
