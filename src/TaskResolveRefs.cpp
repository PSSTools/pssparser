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
#include "TaskCompareTypeRefs.h"
#include "TaskFindPathElem.h"
#include "TaskLinkActionCompRefFields.h"
#include "TaskResolveImports.h"
#include "TaskResolveRef.h"
#include "TaskResolveRefs.h"
#include "pssp/ast/IGenericConstraintDeclBool.h"
#include "pssp/ast/IGenericConstraintDeclValue.h"
#include "pssp/ast/IGenericConstraintParam.h"
#include "TaskSpecializeParameterizedRef.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"
#include "pssp/impl/TaskGetElemSymbolScope.h"
#include "pssp/impl/TaskGetSubscriptSymbolScope.h"
#include "pssp/impl/BuiltinCollectionUtil.h"
#include "pssp/impl/TaskIsPyRef.h"

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
                .resolve(resolvePath(udt->getType_id()->getTarget())));
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
        ast::IScopeChild *c = resolvePath(udt->getType_id()->getTarget());

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

    if (dynamic_cast<ast::IExprAggrLiteral *>(e)
        || dynamic_cast<ast::IExprStructLiteral *>(e)) {
        return TypeCat::Aggregate;
    }

    // A bare name. Anything longer than one element is a member path, whose
    // type needs the walk this classification does not do -- left Unknown.
    ast::IExprRefPathContext *rp = dynamic_cast<ast::IExprRefPathContext *>(e);

    if (rp && !rp->getIs_super() && !rp->getSlice()
        && rp->getHier_id()->getElems().size() == 1
        && !rp->getHier_id()->getElems().at(0)->getParams()
        && rp->getHier_id()->getElems().at(0)->getSubscript().empty()
        && rp->getTarget()) {
        ast::IScopeChild *c = resolvePath(rp->getTarget());

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

void TaskResolveRefs::checkCallArgTypes(
        ast::IExprMemberPathElem  *elem,
        ast::ISymbolFunctionScope *fn) {
    ast::IFunctionPrototype *proto = fn->getPrototypes().front();
    const std::vector<ast::IExprUP> &args = elem->getParams()->getParameters();
    const std::vector<ast::IFunctionParamDeclUP> &params = proto->getParameters();

    for (uint32_t ii=0; ii<args.size() && ii<params.size(); ii++) {
        ast::IFunctionParamDecl *p = params.at(ii).get();

        if (p->getIs_varargs()) {
            // Everything from here on is absorbed, with no declared type to
            // check against.
            break;
        }

        if (p->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType) {
            // A `type` parameter takes a type name, and a `ref` parameter
            // takes a handle. Neither is an ordinary value, and neither is
            // modelled well enough here to have an opinion.
            continue;
        }

        TypeCat want = catOfDataType(p->getType());
        TypeCat got = catOfExpr(args.at(ii).get());

        if (want == TypeCat::Unknown || got == TypeCat::Unknown
            || want == got) {
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
            catName(got),
            p->getName()?p->getName()->getId().c_str():"?",
            catName(want));
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

void TaskResolveRefs::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    DEBUG_ENTER("visitExprRefPathContext %s", i->getHier_id()->getElems().at(0)->getId()->getId().c_str());

    // Restored on every exit, of which this function has many (see the
    // DEBUG_LEAVE calls below), which is why it is a scope guard and not a
    // pair of assignments.
    SaveExpr save_refpath(m_cur_refpath, i);
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
    bool is_builtin_with_methods =
        (!target_s && target_c && isBuiltinWithMethods(target_c));

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

//        if (!ii) {
            if (ii+1 < i->getHier_id()->getElems().size() && elem->getSubscript().size()) {
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
            if (builtinMethods().find(method_name) != builtinMethods().end()) {
                DEBUG("Valid built-in method: %s", method_name.c_str());
                elem->setTarget(-2);
                if (elem->getParams()) {
                    DEBUG_ENTER("Resolve built-in method parameters");
                    for (auto it=elem->getParams()->getParameters().begin();
                        it!=elem->getParams()->getParameters().end(); it++) {
                        (*it)->accept(m_this);
                    }
                    DEBUG_LEAVE("Resolve built-in method parameters");
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

            // A member call -- `comp.f(1)`, `pkg::f(1)`.
            checkCallArity(elem, res.sym);

            // Resolve name references for parameter values
            if (elem->getParams()) {
                elem->getParams()->accept(m_this);
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

void TaskResolveRefs::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    DEBUG_ENTER("visitExprRefPathStatic size=%d", i->getBase().size());
    ast::ISymbolRefPath *target = 0;
    if (i->getIs_global()) {
        DEBUG("TODO: support global-rooted references");
    } else {
        // relative root
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

                if (res.super_idx == 0) {
                    target->getPath().push_back({
                        ast::SymbolRefPathElemKind::ElemKind_ChildIdx,
                        res.idx});
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

void TaskResolveRefs::resolveStaticRootedLeaf(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("resolveStaticRootedLeaf");

    // The leaf of a static-rooted path had no resolution at all -- the branch
    // this replaces was a `DEBUG("TODO")`. `i->getLeaf()->accept()` above
    // descends into the elements' argument expressions, which is why
    // `p::f(nosuch)` was reported, but the element *names* were never looked
    // up in anything: `p::nosuch_f(1)` linked clean, and no qualified call
    // could be checked for arity.
    ast::IScopeChild *target_c =
        m_ctxt->resolveSymbolPathRef(i->getRoot()->getTarget());

    if (!target_c) {
        DEBUG_LEAVE("resolveStaticRootedLeaf -- root path does not resolve");
        return;
    }

    ast::ISymbolScope *scope = TaskGetElemSymbolScope(
        m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(target_c);

    for (uint32_t ii=0; ii<i->getLeaf()->getElems().size(); ii++) {
        ast::IExprMemberPathElem *elem = i->getLeaf()->getElems().at(ii).get();

        if (!scope) {
            // Nothing to search. Quiet on purpose, and for the same reason as
            // the ref-path loop above (see section 29): a scope goes missing
            // when a user-defined type did not resolve, which is the normal
            // state when one file of a multi-file model is parsed alone, and
            // is diagnosed where the type is named rather than here.
            DEBUG("No scope for element %s; not reporting",
                elem->getId()->getId().c_str());
            break;
        }

        if (scope->getOpaque()) {
            DEBUG("Note: scope is opaque; ending search");
            break;
        }

        TaskFindPathElem::Result res = TaskFindPathElem(
            m_ctxt->getDebugMgr(),
            m_ctxt->root()).find(scope, elem->getId());

        if (!res.sym) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error,
                elem->getId()->getLocation(),
                "'%s' has no member named '%s'",
                scope->getName().c_str(),
                elem->getId()->getId().c_str());
            break;
        }

        elem->setTarget(res.idx);
        elem->setSuper(res.super_idx);

        checkCallArity(elem, res.sym);

        scope = TaskGetElemSymbolScope(
            m_ctxt->getDebugMgr(), m_ctxt->root()).resolve(res.sym);
    }

    DEBUG_LEAVE("resolveStaticRootedLeaf");
}

void TaskResolveRefs::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    DEBUG_ENTER("visitExprRefPathStaticRooted %s",
        i->getLeaf()->getElems().at(0)->getId()->getId().c_str());

    // Set here as well as in visitExprRefPathContext: `p::f(1);` is a
    // standalone statement too, and a qualified name builds a *different*
    // expression node. Setting it in only one of the two made every
    // statement-position call through a package qualifier look like an
    // operand, and three tests that had nothing to do with void returns
    // started failing on `p::f(1);` and `p::m(1,2);`.
    SaveExpr save_refpath(m_cur_refpath, i);
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
            resolveStaticRootedLeaf(i);
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
    }
    DEBUG_LEAVE("visitField %s", i->getName()->getId().c_str());
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

        // LRM 20.2.4 c: "A default parameter value shall not be specified in
        // the redeclaration of a function if already declared for the same
        // parameter in a previous declaration, *even if the value is the
        // same*." So the values are deliberately not compared -- specifying
        // one twice is the violation.
        //
        // Stated without "earlier"/"previous", because the prototype list is
        // not in lexical order: a definition's prototype is moved to the
        // front. The rule is symmetric, so nothing is lost by saying so.
        if (b->getDflt() && q->getDflt()) {
            m_ctxt->addMarker(
                MarkerSeverityE::Error, loc,
                "%s of '%s' is given a default value by more than one "
                "declaration; only one declaration may give it",
                paramDesc(idx, b).c_str(), fname.c_str());
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
