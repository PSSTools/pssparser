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
#include "TaskCheckCallArgs.h"
#include "TaskFindPathElem.h"
#include "TaskLinkActionCompRefFields.h"
#include "TaskResolveImports.h"
#include "TaskResolveRef.h"
#include "TaskResolveRefs.h"
#include "TaskTemplateCheck.h"
#include "pssp/ast/IExprTemplateString.h"
#include "pssp/ast/IGenericConstraintDeclBool.h"
#include "pssp/ast/IGenericConstraintDeclValue.h"
#include "pssp/ast/IGenericConstraintParam.h"
#include "TaskSpecializeParameterizedRef.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "pssp/impl/TaskGetElemSymbolScope.h"
#include "pssp/impl/TaskGetSubscriptSymbolScope.h"
#include "pssp/impl/TaskIsPyRef.h"

#include <algorithm>

namespace pssp {


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

void TaskResolveRefs::resolve(ast::ISymbolTypeScope *scope) {
    DEBUG_ENTER("resolve (iterator, scope) %s", scope->getName().c_str());

    if (scope->getPlist()) {
        DEBUG_ENTER("Resolving names in plist");
        scope->getPlist()->accept(m_this);
        DEBUG_LEAVE("Resolving names in plist");
    }

    ast::ITypeScope *target_s = dynamic_cast<ast::ITypeScope *>(scope->getTarget());
    if (target_s->getSuper_t()) {
        target_s->getSuper_t()->accept(m_this);
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

    TaskLinkActionCompRefFields(m_ctxt->getFactory()).link(scope);

    // Check on children
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=scope->getChildren().begin();
        it!=scope->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }

    m_ctxt->symtab()->popScope();

    DEBUG("Removing symbol iterator for body");
    m_ctxt->popSymtab();

    DEBUG_LEAVE("resolve (iterator, scope)");
}

void TaskResolveRefs::visitActivityActionHandleTraversal(ast::IActivityActionHandleTraversal *i) {
    DEBUG_ENTER("visitActivityActionHandleTraversal");
    ast::ISymbolRefPath *target_ref = TaskResolveRef(m_ctxt).resolve(i->getTarget());

    if (!target_ref) {
        return;
    }

    i->getTarget()->setTarget(target_ref);
    ast::IScopeChild *target = resolvePath(i->getTarget()->getTarget());

    if (target) {
        m_ctxt->addRef(i->getLocation().fileid, target->getLocation().fileid);
    }

    ast::IField *field = dynamic_cast<ast::IField *>(target);
    DEBUG("target=%p field=%p", target, field);
    if (!field) {
        DEBUG("Failed to resolve traversal target to a field");
        DEBUG_LEAVE("visitActivityActionHandleTraversal");
        return;
    }
    DEBUG("field: %s", field->getName()->getId().c_str());
    ast::IDataType *field_t = field->getType();
    ast::IDataTypeUserDefined *field_udt = dynamic_cast<ast::IDataTypeUserDefined *>(field_t);

    DEBUG("field_t=%p action_t=%p", field_t, field_udt);
    ast::IScopeChild *field_c = (field_udt && field_udt->getType_id() && field_udt->getType_id()->getTarget())
        ? resolvePath(field_udt->getType_id()->getTarget()) : 0;
    ast::ISymbolScope *field_scope = dynamic_cast<ast::ISymbolScope *>(field_c);
    if (!field_scope) {
        DEBUG("Failed to resolve field type scope");
        DEBUG_LEAVE("visitActivityActionHandleTraversal");
        return;
    }
    DEBUG("field_c=%p field_scope=%s", field_c, field_scope->getName().c_str());
    if (i->getWith_c()) {
        m_ctxt->symtab()->pushScope(field_scope, ast::SymbolRefPathElemKind::ElemKind_Inline);
        m_ctxt->pushInlineCtxt(field_scope);
        DEBUG_ENTER(" ::getWith()");
        i->getWith_c()->accept(m_this);
        DEBUG_LEAVE(" ::getWith()");
        m_ctxt->popInlineCtxt();
        m_ctxt->symtab()->popScope();
    }
    DEBUG_LEAVE("visitActivityActionHandleTraversal");
}
    
void TaskResolveRefs::visitActivityActionTypeTraversal(ast::IActivityActionTypeTraversal *i) {
    DEBUG_ENTER("visitActivityActionTypeTraversal");
    i->getTarget()->accept(m_this);
    ast::IDataTypeUserDefined *field_udt = i->getTarget(); // <ast::IDataTypeUserDefined *>(i->getTarget());
//    DEBUG("--> resolve field_udt->getType_id()");
//    field_udt->getType_id()->accept(m_this);
//    DEBUG("<-- resolve field_udt->getType_id()");
//    ast::IScopeChild *field_c = resolvePath(field_udt->getType_id()->getTarget());
    if (field_udt->getType_id()->getTarget()) {
        ast::IScopeChild *field_c = resolvePath(field_udt->getType_id()->getTarget());
        ast::ISymbolScope *field_scope = dynamic_cast<ast::ISymbolScope *>(field_c);
        if (i->getWith_c()) {
            m_ctxt->symtab()->pushScope(field_scope, ast::SymbolRefPathElemKind::ElemKind_Inline);
            m_ctxt->pushInlineCtxt(field_scope);
            DEBUG_ENTER(" ::getWith()");
            i->getWith_c()->accept(m_this);
            DEBUG_LEAVE(" ::getWith()");
            m_ctxt->popInlineCtxt();
            m_ctxt->symtab()->popScope();
        }
    }
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
    m_ctxt->symtab()->pushScope(i);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=i->getChildren().begin();
        it!=i->getChildren().end(); it++) {
        (*it)->accept(m_this);
    }
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitExecScope");
}

void TaskResolveRefs::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext %s", i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
    // Find the first path element
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(
        i->getHier_id()->getElems().at(0)->getId());

    if (!target) {
        const std::string &name = i->getHier_id()->getElems().at(0)->getId()->getId();

        // Skip resolution errors for generic constraint parameters
        if (isGenericConstraintParam(name)) {
            DEBUG("Skipping resolution for generic constraint param '%s'", name.c_str());
            DEBUG_LEAVE("visitExprRefPathContext -- generic param");
            return;
        }

        std::string suggestion = findCloseMatch_rr(
            name, dynamic_cast<ast::ISymbolScope *>(m_ctxt->root()));
        if (suggestion.empty() && m_ctxt->symtab()) {
            suggestion = findCloseMatch_rr(
                name, m_ctxt->symtab()->getScope());
        }
        if (suggestion.empty()) {
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

    // Set root reference
    i->setTarget(target);

    ast::IScopeChild *target_c = TaskResolveSymbolPathRef(
        m_ctxt->getDebugMgr(), 
        m_ctxt->root(),
        m_ctxt->inlineCtxt()).resolve(target);
    ast::ISymbolScope *target_s = 0;
    
    if (target_c) {
        target_s = TaskGetElemSymbolScope(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target_c);
    }

    DEBUG("target_c=%p target_s=%p", target_c, target_s);

    // Check if target_c is a field or local variable with a built-in type that has methods (e.g., string)
    bool is_builtin_with_methods = false;
    bool is_string_target = false;
    ast::IDataType *target_type = 0;

    if (!target_s && target_c) {
        // Check if it's a field declaration
        ast::IField *field = dynamic_cast<ast::IField *>(target_c);
        if (field && field->getType()) {
            target_type = field->getType();
        }
        
        // Check if it's a procedural data declaration (local variable)
        if (!target_type) {
            ast::IProceduralStmtDataDeclaration *var_decl = 
                dynamic_cast<ast::IProceduralStmtDataDeclaration *>(target_c);
            if (var_decl && var_decl->getDatatype()) {
                target_type = var_decl->getDatatype();
            }
        }
        
        // Check if the type is a string
        if (target_type) {
            ast::IDataTypeString *string_type = dynamic_cast<ast::IDataTypeString *>(target_type);
            if (string_type) {
                is_builtin_with_methods = true;
                is_string_target = true;
                DEBUG("Found string variable '%s' - allowing method calls",
                    i->getHier_id()->getElems().at(0)->getId()->getId().c_str());
            }
            if (!is_builtin_with_methods) {
                ast::IDataTypeUserDefined *udt = dynamic_cast<ast::IDataTypeUserDefined *>(target_type);
                if (udt && udt->getType_id() && !udt->getType_id()->getElems().empty()) {
                    const std::string &tname = udt->getType_id()->getElems().at(0)->getId()->getId();
                    static const std::set<std::string> collection_types = {
                        "list", "array", "set", "map"
                    };
                    if (collection_types.find(tname) != collection_types.end()) {
                        is_builtin_with_methods = true;
                        DEBUG("Found collection variable '%s' (type %s) - allowing method calls",
                            i->getHier_id()->getElems().at(0)->getId()->getId().c_str(),
                            tname.c_str());
                    }
                }
            }
        }
    }

    if (!target_s && !is_builtin_with_methods && i->getHier_id()->getElems().size() > 1) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getHier_id()->getElems().at(0)->getId()->getLocation(),
            "root ref-path element %s is not a composite scope",
            i->getHier_id()->getElems().at(0)->getId()->getId().c_str());

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
            TaskCheckCallArgs(m_ctxt).check(target_c, elem);
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
                    DEBUG_ERROR("Handle multi-dim array subscript");
                }
                target_s = TaskGetSubscriptSymbolScope(
                    m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(
                        target_c
                    );
            }
            if (!ii) {
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
        if (!target_s && is_builtin_with_methods && ii == 1) {
            // This is a method call on a built-in type - validate method name
            std::string method_name = elem->getId()->getId();
            static const std::set<std::string> valid_collection_methods = {
                "size",
                "push_back", "pop_back", "push_front", "pop_front",
                "insert", "delete", "clear",
                "contains", "find",
                "sort", "rsort", "shuffle", "reverse", "unique",
                "join", "str_from_chars",
                "keys", "values",
                "front", "back",
                "set", "get"
            };

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
                found = (valid_collection_methods.find(method_name)
                            != valid_collection_methods.end());
            }

            if (found) {
                DEBUG("Valid built-in method: %s", method_name.c_str());
                // -2 marks "resolved, but not to an index in the enclosing
                // scope". The element path stops here either way, so the
                // prototype is used for checking only and is not recorded.
                elem->setTarget(-2);
                if (elem->getParams()) {
                    DEBUG_ENTER("Resolve built-in method parameters");
                    for (auto it=elem->getParams()->getParameters().begin();
                        it!=elem->getParams()->getParameters().end(); it++) {
                        (*it)->accept(m_this);
                    }
                    DEBUG_LEAVE("Resolve built-in method parameters");
                    if (proto) {
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

        TaskFindPathElem::Result res = TaskFindPathElem(
            m_ctxt->getDebugMgr(), 
            m_ctxt->root()).find(
                target_s,
                elem->getId()
            );

        std::unordered_map<std::string, int32_t>::const_iterator it = 
            target_s->getSymtab().find(elem->getId()->getId());
        
        if (!res.sym) {
            static const std::set<std::string> valid_collection_methods = {
                "size",
                "push_back", "pop_back", "push_front", "pop_front",
                "insert", "delete", "clear",
                "contains", "find",
                "sort", "rsort", "shuffle", "reverse", "unique",
                "join", "str_from_chars",
                "keys", "values",
                "front", "back",
                "set", "get"
            };
            bool is_collection_method = false;
            auto isCollectionScope = [](ast::ISymbolScope *s) -> bool {
                if (!s) return false;
                const std::string &n = s->getName();
                return (n.rfind("list", 0) == 0 || n.rfind("array", 0) == 0 ||
                        n.rfind("set", 0) == 0 || n.rfind("map", 0) == 0);
            };
            if (isCollectionScope(target_s)) {
                DEBUG("Collection method check: target_s name='%s' method='%s'",
                    target_s->getName().c_str(), elem->getId()->getId().c_str());
                const std::string &mname = elem->getId()->getId();
                if (valid_collection_methods.count(mname)) {
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

            // Resolve name references for parameter values
            if (elem->getParams()) {
                elem->getParams()->accept(m_this);
                TaskCheckCallArgs(m_ctxt).check(res.sym, elem);
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
                    DEBUG_ERROR("target_s is null");
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
                        DEBUG_ERROR("Handle multi-dim array subscript");
                    }
                    target_s = TaskGetSubscriptSymbolScope(
                        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(
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

void TaskResolveRefs::visitActivityForeach(ast::IActivityForeach *i) {
    DEBUG_ENTER("visitActivityForeach");
    // Push the body scope FIRST so that the index variable (idx_id) is in scope
    // when resolving the target expression (e.g., `count[j]` where `j` is idx_id).
    ast::ISymbolScope *body_scope =
        i->getBody() ? dynamic_cast<ast::ISymbolScope*>(i->getBody()) : nullptr;
    if (body_scope) {
        m_ctxt->symtab()->pushScope(body_scope);
    }
    visitActivityLabeledStmt(i);
    if (i->getIt_id())  { i->getIt_id()->accept(this); }
    if (i->getIdx_id()) { i->getIdx_id()->accept(this); }
    if (i->getTarget()) { i->getTarget()->accept(this); }
    if (body_scope) {
        m_ctxt->symtab()->popScope();
    }
    if (i->getBody()) { i->getBody()->accept(this); }
    DEBUG_LEAVE("visitActivityForeach");
}


void TaskResolveRefs::visitExprRefPathId(ast::IExprRefPathId *i) {
    DEBUG_ENTER("visitExprRefPathId %s", i->getId()->getId().c_str());
    ast::ISymbolRefPath *target = TaskResolveRef(m_ctxt).resolve(i);
    if (!target) {
        m_ctxt->addErrorMarker(
            i->getId()->getLocation(),
            "failed to resolve ref-path %s", 
            i->getId()->getId().c_str());
    } else {
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }
    i->setTarget(target);
    DEBUG_LEAVE("visitExprRefPathId");
}

void TaskResolveRefs::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic size=%d", i->getBase().size());
    ast::ISymbolRefPath *target = 0;
    if (i->getIs_global()) {
        DEBUG("TODO: support global-rooted references");
    } else {
        // relative root
        ast::ISymbolRefPath *target = 0;
        ast::IScopeChild *target_s = 0;
        bool in_pyref = false;
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getBase().begin();
            it!=i->getBase().end(); it++) {
            if (it==i->getBase().begin()) {
                target = TaskResolveRef(m_ctxt).resolve((*it)->getId());
                
                if (!target) {
                    addMarker(
                        MarkerSeverityE::Error,
                        (*it)->getId()->getLocation(),
                        "failed to resolve symbol %s",
                        (*it)->getId()->getId().c_str());
                    break;
                }

                if ((*it)->getParams()) {
                    DEBUG("Ref elem %d is parameterized", (it-i->getBase().begin()));

                    // Build out parameter value list
                    target = TaskSpecializeParameterizedRef(m_ctxt).specialize(
                            target, 
                            (*it)->getParams());

                    // TODO: do we need to delete target?
                }

                target_s = m_ctxt->resolveSymbolPathRef(target);

                if ((*it)->getParams()) {
                    DEBUG("Ref elem is parameterized");
                }

                if (!in_pyref) {
                    in_pyref |= TaskIsPyRef(m_ctxt->getDebugMgr(), m_ctxt->root()).check(target_s);
                    if (in_pyref) {
                        target->setPyref_idx(0);
                    } else {
                    }
                }
            } else if (!in_pyref) {
                // Need to resolve within root element ... unless we're down a Python scope
                // Visit the element to resolve internal references
                (*it)->accept(m_this);

            } else {
                DEBUG("element is inside a pyref path");
            }
        }
        i->setTarget(target);
    }

    if (target) {
        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getBase().front()->getId()->getLocation().fileid,
            target_c->getLocation().fileid);
    }
    DEBUG_LEAVE("visitExprRefPathStatic");
}

void TaskResolveRefs::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("visitExprRefPathStaticRooted %s",
        i->getLeaf()->getElems().at(0)->getId()->getId().c_str());
    // Resolve the root
    if (i->getRoot()->getIs_global()) {
        ast::IExprId *id = i->getLeaf()->getElems().at(0)->getId();
        DEBUG("Global reference -- first find leaf %s", id->getId().c_str());
        std::unordered_map<std::string,int32_t>::const_iterator it;
        const std::unordered_map<std::string,int32_t> &symtab = 
            m_ctxt->symtab()->getRootScope()->getSymtab();
        
        if ((it=symtab.find(id->getId())) == symtab.end()) {
            DEBUG_ERROR("Failed to resolve leaf %s", id->getId().c_str());
            for (it=symtab.begin(); it!=symtab.end(); it++) {
                DEBUG("Symbol: %s", it->first.c_str());
            }
        } else {
            ast::ISymbolRefPath *ref = 
                m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath();
            ast::SymbolRefPathElem elem;
            elem.kind = ast::SymbolRefPathElemKind::ElemKind_ChildIdx;
            elem.idx = it->second;
            ref->getPath().push_back(elem);
            i->getRoot()->setTarget(ref);
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
            DEBUG("TODO: visitExprRefPathStaticRooted");
        }
    }

    DEBUG_LEAVE("visitExprRefPathStaticRooted");
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
    }
    DEBUG_LEAVE("visitFunctionPrototype");
} 

void TaskResolveRefs::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    DEBUG_ENTER("visitProceduralStmtRepeat %d", i->getSymtab().size());
    m_ctxt->symtab()->pushScope(i);
    i->getBody()->accept(m_this);
    m_ctxt->symtab()->popScope();
    DEBUG_LEAVE("visitProceduralStmtRepeat");
}

void TaskResolveRefs::visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) {
    DEBUG_ENTER("visitProceduralStmtForeach %d", i->getSymtab().size());
    // Resolve the collection path in the OUTER scope (it must not see the
    // loop variables registered on the foreach node itself).
    if (i->getPath()) { i->getPath()->accept(m_this); }
    // Push the foreach scope so the iterator/index variables are visible while
    // resolving references in the body (e.g. `arr[i]`).
    m_ctxt->symtab()->pushScope(i);
    if (i->getBody()) { i->getBody()->accept(m_this); }
    m_ctxt->symtab()->popScope();
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
    const std::string &name = i->getLhs()->getId();

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
            i->getLhs()->getLocation(),
            "unknown identifier '%s'",
            name.c_str());
    } else if (!in_template) {
        m_ctxt->addMarker(
            MarkerSeverityE::Error,
            i->getLhs()->getLocation(),
            "template assignment target '%s' is not declared within this "
            "template string",
            name.c_str());
    }

    DEBUG_LEAVE("visitTemplateAssign");
}

void TaskResolveRefs::visitSymbolScope(ast::ISymbolScope *i) {
    DEBUG_ENTER("visitSymbolScope %s", i->getName().c_str());
    /*
    if (i->getName() != "") {
        if (m_ctxt->symtab()->pushNamedScope(i->getName()) == -1) {
            // TODO: internal error
            fprintf(stdout, "Internal Error: no scope named %s in %s\n", 
                i->getName().c_str(),
                m_ctxt->symtab()->getScope()->getName().c_str());
        }
    } else {
        */
        m_ctxt->symtab()->pushScope(i);
//    }

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
        it->get()->accept(this);
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
            i->getBody()->accept(m_this);
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

void TaskResolveRefs::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());
    DEBUG_ENTER("visitSymbolTypeScope %s (param=%s specialized=%s)", 
        i->getName().c_str(),
        (i_ts->getParams())?"true":"false",
        (i_ts->getParams() && i_ts->getParams()->getSpecialized())?"true":"false");
    if (i_ts->getParams() && !i_ts->getParams()->getSpecialized()) {
        DEBUG("Note: Skipping symbol resolution in an unspecialized templated type");
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

        // Check on children
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=i->getChildren().begin();
            it!=i->getChildren().end(); it++) {
            (*it)->accept(m_this);
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

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override {
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
        m_ctxt->addMarker(
            MarkerSeverityE::Warn,
            i->getLocation(),
            "unknown annotation type '%s'; annotation disregarded",
            type_name.c_str());
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
        const std::string &name = param->getName()->getId();

        // Use TaskFindPathElem rather than the scope's own symtab: fields
        // contributed by `extend annotation` are not merged into the symbol
        // scope's children, and a plain symtab lookup would report them as
        // unknown.
        TaskFindPathElem::Result res = {0, -1, -1};
        if (decl_s) {
            res = TaskFindPathElem(
                m_ctxt->getDebugMgr(),
                m_ctxt->root()).find(decl_s, param->getName());
        }

        if (decl_s && !res.sym) {
            m_ctxt->addErrorMarker(
                param->getLocation(),
                "unknown identifier '%s' in annotation type '%s'",
                name.c_str(),
                type_name.c_str());
            continue;
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

        ast::IScopeChild *target_c = m_ctxt->resolveSymbolPathRef(target);
        m_ctxt->addRef(
            i->getLocation().fileid,
            target_c->getLocation().fileid);
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

    // Register parameter names so they are not flagged as unknown
    std::set<std::string> saved = m_generic_constraint_params;
    for (auto &p : i->getParameters()) {
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

    std::set<std::string> saved = m_generic_constraint_params;
    for (auto &p : i->getParameters()) {
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

ast::IScopeChild *TaskResolveRefs::resolvePath(ast::ISymbolRefPath *path) {
    ast::ISymbolScope *scope = m_ctxt->root();
    ast::IScopeChild *ret = m_ctxt->root();

    if (!path) return ret;

    for (std::vector<ast::SymbolRefPathElem>::const_iterator
        it=path->getPath().begin();
        it!=path->getPath().end(); it++) {
        if (!scope || it->idx >= (int32_t)scope->getChildren().size()) {
            return 0;
        }
        ret = scope->getChildren().at(it->idx).get();

        if (it+1 != path->getPath().end()) {
            scope = dynamic_cast<ast::ISymbolScope *>(ret);
        }
    }
    
    return ret;
}

dmgr::IDebug *TaskResolveRefs::m_dbg = 0;

}
