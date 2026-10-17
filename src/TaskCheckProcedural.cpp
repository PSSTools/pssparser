/**
 * TaskCheckProcedural.cpp
 *
 * Copyright 2026 Matthew Ballance and Contributors
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
 */
#include "dmgr/impl/DebugMacros.h"
#include "pssp/ast/IActivityMatch.h"
#include "pssp/ast/IActivityMatchChoice.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IExecBlock.h"
#include "pssp/ast/IExecTargetTemplateBlock.h"
#include "pssp/ast/IProceduralStmtYield.h"
#include "pssp/ast/IStruct.h"
#include "FunctionScopeUtil.h"
#include "pssp/ast/IExprHierarchicalId.h"
#include "pssp/ast/IExprRefPathContext.h"
#include "pssp/ast/IExprRefPathStatic.h"
#include "pssp/ast/IExprRefPathStaticRooted.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IFunctionDefinition.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IFunctionPrototype.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IMethodParameterList.h"
#include "pssp/ast/IProceduralStmtAssignment.h"
#include "pssp/ast/IProceduralStmtBreak.h"
#include "pssp/ast/IProceduralStmtContinue.h"
#include "pssp/ast/IProceduralStmtForeach.h"
#include "pssp/ast/IProceduralStmtMatch.h"
#include "pssp/ast/IProceduralStmtMatchChoice.h"
#include "pssp/ast/IProceduralStmtRepeat.h"
#include "pssp/ast/IProceduralStmtRepeatWhile.h"
#include "pssp/ast/IProceduralStmtWhile.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "pssp/ast/ITypeIdentifierElem.h"
#include "pssp/impl/NodeKind.h"
#include "TaskCheckCallArgs.h"
#include "TaskCheckProcedural.h"

namespace pssp {

dmgr::IDebug *TaskCheckProcedural::m_dbg = 0;

TaskCheckProcedural::TaskCheckProcedural(ResolveContext *ctxt) :
        m_ctxt(ctxt), m_typer(ctxt), m_loop_depth(0), m_plat(Plat::Any) {
    DEBUG_INIT("pssp::TaskCheckProcedural", ctxt->getDebugMgr());
}

TaskCheckProcedural::~TaskCheckProcedural() {

}

void TaskCheckProcedural::check(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("check");
    // The user's files, as written: not the builtins (fileid -1) nor the
    // bundled core library (0). Each body is reached once this way.
    for (uint32_t i=0; i<root->getUnits().size(); i++) {
        ast::IGlobalScope *unit = root->getUnits().at(i).get();
        if (unit->getFileid() >= 1) {
            m_loop_depth = 0;
            m_foreach.clear();
            unit->accept(m_this);
        }
    }
    DEBUG_LEAVE("check");
}

// ---------------------------------------------------------------------------
// Loops: the context break/continue and the foreach rules need
// ---------------------------------------------------------------------------

void TaskCheckProcedural::visitFunctionDefinition(ast::IFunctionDefinition *i) {
    int32_t depth = m_loop_depth;
    std::vector<Foreach> fe;
    fe.swap(m_foreach);
    m_loop_depth = 0;
    Plat plat = m_plat;
    std::string where = m_where;
    ast::IFunctionPrototype *proto = i->getProto();
    bool tgt = (proto && proto->getIs_target()) || i->getPlat() == ast::PlatQual::PlatQual_Target;
    bool slv = (proto && proto->getIs_solve()) || i->getPlat() == ast::PlatQual::PlatQual_Solve;
    m_plat = (tgt && !slv) ? Plat::Target : (slv && !tgt) ? Plat::Solve : Plat::Any;
    m_where = std::string((m_plat == Plat::Target) ? "target" : "solve") + " function '"
        + ((proto && proto->getName()) ? proto->getName()->getId() : "?") + "'";
    ast::VisitorBase::visitFunctionDefinition(i);
    m_loop_depth = depth;
    m_foreach.swap(fe);
    m_plat = plat;
    m_where = where;
}

static const char *execKindName(ast::ExecKind k) {
    switch (k) {
        case ast::ExecKind::ExecKind_Body: return "body";
        case ast::ExecKind::ExecKind_Header: return "header";
        case ast::ExecKind::ExecKind_Declaration: return "declaration";
        case ast::ExecKind::ExecKind_RunStart: return "run_start";
        case ast::ExecKind::ExecKind_RunEnd: return "run_end";
        case ast::ExecKind::ExecKind_InitDown: return "init_down";
        case ast::ExecKind::ExecKind_InitUp: return "init_up";
        case ast::ExecKind::ExecKind_PreSolve: return "pre_solve";
        case ast::ExecKind::ExecKind_PostSolve: return "post_solve";
        case ast::ExecKind::ExecKind_PreBody: return "pre_body";
        default: return "file";
    }
}

static bool isSolveKind(ast::ExecKind k) {
    return k == ast::ExecKind::ExecKind_InitDown || k == ast::ExecKind::ExecKind_InitUp
        || k == ast::ExecKind::ExecKind_PreSolve || k == ast::ExecKind::ExecKind_PostSolve
        || k == ast::ExecKind::ExecKind_PreBody;
}

static bool isTargetKind(ast::ExecKind k) {
    return k == ast::ExecKind::ExecKind_Body || k == ast::ExecKind::ExecKind_RunStart
        || k == ast::ExecKind::ExecKind_RunEnd;
}

void TaskCheckProcedural::visitExecBlock(ast::IExecBlock *i) {
    // 20.1.2: where each exec kind is valid. The type is the block's
    // parent as written (an extension's blocks are its own, and not judged).
    ast::IScope *owner = i->getParent();
    const char *kname = execKindName(i->getKind());
    bool comp = NodeKind::cast<ast::IComponent>(owner) != 0;
    bool action = NodeKind::cast<ast::IAction>(owner) != 0;
    bool strct = NodeKind::cast<ast::IStruct>(owner) != 0;
    if (comp || action || strct) {
        const char *bad_in = 0, *valid_in = 0;
        switch (i->getKind()) {
            // (init_down/init_up outside a component is not judged yet.)
            case ast::ExecKind::ExecKind_PreSolve:
            case ast::ExecKind::ExecKind_PostSolve:
            case ast::ExecKind::ExecKind_PreBody:
                if (comp) {
                    bad_in = "a component";
                    valid_in = "actions, objects and structs";
                }
                break;
            case ast::ExecKind::ExecKind_Body:
                if (!action) {
                    bad_in = (comp) ? "a component" : "a struct or object";
                    valid_in = "actions";
                }
                break;
            default:
                break;
        }
        if (bad_in) {
            m_ctxt->addErrorMarker(i->getLocation(),
                "exec %s is not valid in %s: it is valid in %s (LRM 20.1.2)",
                kname, bad_in, valid_in);
        }
    }

    int32_t depth = m_loop_depth;
    std::vector<Foreach> fe;
    fe.swap(m_foreach);
    m_loop_depth = 0;
    Plat plat = m_plat;
    std::string where = m_where;
    m_plat = (isSolveKind(i->getKind())) ? Plat::Solve
        : (isTargetKind(i->getKind())) ? Plat::Target : Plat::Any;
    m_where = std::string("exec ") + kname;
    ast::VisitorBase::visitExecBlock(i);
    m_loop_depth = depth;
    m_foreach.swap(fe);
    m_plat = plat;
    m_where = where;
}

void TaskCheckProcedural::visitExecTargetTemplateBlock(ast::IExecTargetTemplateBlock *i) {
    // 20.5: "Target-template implementations may not be used for solve
    // execs (init_down, init_up, pre_solve, post_solve, and pre_body)."
    if (isSolveKind(i->getKind())) {
        m_ctxt->addErrorMarker(i->getLocation(),
            "a target-template exec block cannot be %s, a solve exec kind (LRM 20.5)",
            execKindName(i->getKind()));
    }
    ast::VisitorBase::visitExecTargetTemplateBlock(i);
}

void TaskCheckProcedural::visitProceduralStmtYield(ast::IProceduralStmtYield *i) {
    // 20.7.14 a: "The yield statement may only be used in target exec blocks
    // and functions"; ruling R20 makes it target-only. An unqualified
    // function may hold one.
    if (m_plat == Plat::Solve) {
        m_ctxt->addErrorMarker(i->getLocation(),
            "'yield' may only be used in target code; %s is solve code "
            "(LRM 20.7.14 a, ruling R20)", m_where.c_str());
    }
}

TaskCheckProcedural::Plat TaskCheckProcedural::calleePlat(
        ast::ISymbolFunctionScope   *fn,
        bool                        *templ) {
    *templ = false;
    bool tgt = false, slv = false;
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
            it=fn->getPrototypes().begin(); it!=fn->getPrototypes().end(); it++) {
        tgt |= (*it)->getIs_target();
        slv |= (*it)->getIs_solve();
    }
    if (functionImplementation(fn) == FunctionImpl::TargetTemplate) {
        *templ = true;
        return Plat::Target;
    }
    return (tgt && !slv) ? Plat::Target : (slv && !tgt) ? Plat::Solve : Plat::Any;
}

void TaskCheckProcedural::checkCallPlatform(
        ast::IExprMemberPathElem    *elem,
        ast::ISymbolFunctionScope   *fn) {
    if (m_plat == Plat::Any) {
        return;
    }
    bool templ = false;
    Plat p = calleePlat(fn, &templ);
    if (p == Plat::Any || p == m_plat) {
        return;
    }
    // Held back pending a ruling: the core library's `print` is declared
    // `solve` (21.1.2), so a target exec may not call it by 20.2.1.3 -- but
    // pssc's target-side backends lower it in `exec body`, and many models
    // do. Not reported until that is decided (06-front-end-checks F22).
    if (m_plat == Plat::Target && fn->getName() == "print"
            && fn->getPrototypes().size()
            && fn->getPrototypes().front()->getName()->getLocation().fileid < 1) {
        return;
    }
    // 20.2.1.3: "Functions restricted to the solve platform shall not be
    // called directly or indirectly from target execs ... Similarly,
    // functions restricted to the target platform shall not be called from
    // solve execs"; a function of either kind by the same token. 20.1.2:
    // init_down and init_up "may not call target template functions".
    m_ctxt->addErrorMarker(elem->getId()->getLocation(),
        "'%s' is %s and cannot be called from %s, which is %s code (LRM 20.2.1.3)",
        elem->getId()->getId().c_str(),
        (templ) ? "a target-template function" :
            (p == Plat::Target) ? "a target function" : "a solve function",
        m_where.c_str(),
        (m_plat == Plat::Target) ? "target" : "solve");
}

void TaskCheckProcedural::loopBody(ast::IScopeChild *body) {
    if (body) {
        m_loop_depth++;
        body->accept(m_this);
        m_loop_depth--;
    }
}

void TaskCheckProcedural::visitProceduralStmtRepeat(ast::IProceduralStmtRepeat *i) {
    if (i->getCount()) {
        i->getCount()->accept(m_this);
    }
    loopBody(i->getBody());
}

void TaskCheckProcedural::visitProceduralStmtRepeatWhile(ast::IProceduralStmtRepeatWhile *i) {
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    loopBody(i->getBody());
}

void TaskCheckProcedural::visitProceduralStmtWhile(ast::IProceduralStmtWhile *i) {
    if (i->getExpr()) {
        i->getExpr()->accept(m_this);
    }
    loopBody(i->getBody());
}

void TaskCheckProcedural::visitProceduralStmtForeach(ast::IProceduralStmtForeach *i) {
    if (i->getPath()) {
        i->getPath()->accept(m_this);
    }

    // The builder registers the iterator and index on the loop node; a
    // reference to either in the body binds to that declaration.
    Foreach fe;
    fe.stmt = i;
    fe.coll = lvalueOf(i->getPath());
    fe.it = 0;
    fe.idx = 0;
    if (i->getIt_id()) {
        auto it = i->getSymtab().find(i->getIt_id()->getId());
        if (it != i->getSymtab().end() && it->second >= 0
                && it->second < (int32_t)i->getChildren().size()) {
            fe.it = i->getChildren().at(it->second).get();
        }
    }
    if (i->getIdx_id()) {
        auto it = i->getSymtab().find(i->getIdx_id()->getId());
        if (it != i->getSymtab().end() && it->second >= 0
                && it->second < (int32_t)i->getChildren().size()) {
            fe.idx = i->getChildren().at(it->second).get();
        }
    }
    m_foreach.push_back(fe);
    loopBody(i->getBody());
    m_foreach.pop_back();
}

void TaskCheckProcedural::visitProceduralStmtBreak(ast::IProceduralStmtBreak *i) {
    if (m_loop_depth == 0) {
        m_ctxt->addErrorMarker(i->getLocation(),
            "'break' may only appear within a loop statement: repeat, while or "
            "foreach (LRM 20.7.11 b)");
    }
}

void TaskCheckProcedural::visitProceduralStmtContinue(ast::IProceduralStmtContinue *i) {
    if (m_loop_depth == 0) {
        m_ctxt->addErrorMarker(i->getLocation(),
            "'continue' may only appear within a loop statement: repeat, while or "
            "foreach (LRM 20.7.11 b)");
    }
}

// ---------------------------------------------------------------------------
// match: at most one default branch
// ---------------------------------------------------------------------------

void TaskCheckProcedural::visitProceduralStmtMatch(ast::IProceduralStmtMatch *i) {
    bool seen = false;
    for (std::vector<ast::IProceduralStmtMatchChoiceUP>::const_iterator
            it=i->getChoices().begin(); it!=i->getChoices().end(); it++) {
        if (!(*it)->getIs_default()) {
            continue;
        }
        if (seen) {
            // The builder gives a choice no location; its body has one.
            ast::Location loc = (*it)->getLocation();
            if (loc.lineno <= 0 && (*it)->getBody()) {
                loc = (*it)->getBody()->getLocation();
            }
            if (loc.lineno <= 0) {
                loc = i->getLocation();
            }
            m_ctxt->addErrorMarker(loc,
                "a match statement may have at most one default branch; this is "
                "a second one (LRM 20.7.10 f)");
        }
        seen = true;
    }
    ast::VisitorBase::visitProceduralStmtMatch(i);
}

void TaskCheckProcedural::visitActivityMatch(ast::IActivityMatch *i) {
    bool seen = false;
    for (std::vector<ast::IActivityMatchChoiceUP>::const_iterator
            it=i->getChoices().begin(); it!=i->getChoices().end(); it++) {
        if (!(*it)->getIs_default()) {
            continue;
        }
        if (seen) {
            // A choice is not a ScopeChild and has no location of its own;
            // its body has.
            ast::Location loc = ((*it)->getBody())
                ? (*it)->getBody()->getLocation() : i->getLocation();
            if (loc.lineno <= 0) {
                loc = i->getLocation();
            }
            m_ctxt->addErrorMarker(loc,
                "a match statement may have at most one default branch; this is "
                "a second one (LRM 11.4.6 f)");
        }
        seen = true;
    }
    ast::VisitorBase::visitActivityMatch(i);
}

// ---------------------------------------------------------------------------
// References
// ---------------------------------------------------------------------------

TaskCheckProcedural::LValue TaskCheckProcedural::lvalueOfElems(
        const std::vector<ast::IExprMemberPathElemUP>   &elems,
        uint32_t                                        n,
        ast::IScopeChild                                *first_decl) {
    LValue ret;
    for (uint32_t k=0; k<n && k<elems.size(); k++) {
        ast::IExprMemberPathElem *elem = elems.at(k).get();
        if (elem->getParams()) {
            // A call's result is a value, not a variable.
            return LValue();
        }
        PathStep step;
        step.elem = elem;
        step.id = elem->getId();
        step.decl = elem->getId()->getDecl();
        if (!step.decl && k == 0) {
            step.decl = first_decl;
        }
        ret.steps.push_back(step);
    }
    ret.valid = (ret.steps.size() > 0);
    return ret;
}

TaskCheckProcedural::LValue TaskCheckProcedural::lvalueOf(ast::IExpr *e) {
    NodeKind nk(e);
    if (ast::IExprRefPathStaticRooted *r = nk.as<ast::IExprRefPathStaticRooted>()) {
        if (!r->getLeaf() || r->getSlice()) {
            return LValue();
        }
        return lvalueOfElems(r->getLeaf()->getElems(),
            r->getLeaf()->getElems().size(), 0);
    } else if (ast::IExprRefPathContext *r = nk.as<ast::IExprRefPathContext>()) {
        if (!r->getHier_id() || !r->getTarget()) {
            return LValue();
        }
        return lvalueOfElems(r->getHier_id()->getElems(),
            r->getHier_id()->getElems().size(),
            m_ctxt->resolveSymbolPathRef(r->getTarget()));
    } else if (ast::IExprRefPathStatic *r = nk.as<ast::IExprRefPathStatic>()) {
        if (!r->getTarget() || !r->getBase().size()) {
            return LValue();
        }
        LValue ret;
        PathStep step;
        step.elem = 0;
        step.id = r->getBase().back()->getId();
        step.decl = m_ctxt->resolveSymbolPathRef(r->getTarget());
        ret.steps.push_back(step);
        ret.valid = true;
        return ret;
    }
    return LValue();
}

int32_t TaskCheckProcedural::constStep(const LValue &lv) {
    for (uint32_t k=0; k<lv.steps.size(); k++) {
        NodeKind nk(lv.steps.at(k).decl);
        if (ast::IField *f = nk.as<ast::IField>()) {
            if ((f->getAttr() & ast::FieldAttr::Const) != ast::FieldAttr::NoFlags) {
                return k;
            }
        } else if (ast::IFunctionParamDecl *p = nk.as<ast::IFunctionParamDecl>()) {
            if (k == 0 && p->getIs_const()) {
                return k;
            }
        }
    }
    return -1;
}

static bool hasSubscript(const ast::IExprMemberPathElem *elem) {
    return elem && const_cast<ast::IExprMemberPathElem *>(elem)->getSubscript().size();
}

// ---------------------------------------------------------------------------
// Assignments
// ---------------------------------------------------------------------------

void TaskCheckProcedural::visitProceduralStmtAssignment(ast::IProceduralStmtAssignment *i) {
    ast::VisitorBase::visitProceduralStmtAssignment(i);

    LValue lv = lvalueOf(i->getLhs());
    if (!lv.valid) {
        return;
    }
    checkConstWrite(lv);
    checkSubstringWrite(i->getLhs(), lv);
    checkForeachWrite(lv, 0);
}

void TaskCheckProcedural::checkConstWrite(const LValue &lv) {
    int32_t k = constStep(lv);
    if (k < 0) {
        return;
    }
    const PathStep &step = lv.steps.at(k);
    // A part of it: a member past it, or an element of it.
    bool part = (k+1 < (int32_t)lv.steps.size()) || hasSubscript(step.elem);
    const char *name = step.id->getId().c_str();
    if (NodeKind::cast<ast::IFunctionParamDecl>(step.decl)) {
        if (part) {
            m_ctxt->addErrorMarker(step.id->getLocation(),
                "an element or member of const parameter '%s' cannot be changed "
                "in the function body (LRM 20.2.3)", name);
        } else {
            m_ctxt->addErrorMarker(step.id->getLocation(),
                "parameter '%s' is const, so its value cannot be changed in the "
                "function body (LRM 20.2.3)", name);
        }
    } else if (part) {
        m_ctxt->addErrorMarker(step.id->getLocation(),
            "an element or member of constant '%s' cannot be assigned: a constant's "
            "elements are constants too (LRM 7.1)", name);
    } else {
        m_ctxt->addErrorMarker(step.id->getLocation(),
            "constant '%s' cannot be assigned: a constant cannot appear on the left "
            "of an assignment (LRM 7.1)", name);
    }
}

void TaskCheckProcedural::checkSubstringWrite(ast::IExpr *lhs, const LValue &lv) {
    const PathStep &last = lv.steps.back();
    if (!hasSubscript(last.elem) || !last.decl) {
        return;
    }
    ExprType t = m_typer.typeOfDecl(last.decl);
    for (std::vector<ast::IExprUP>::const_iterator
            it=last.elem->getSubscript().begin();
            t.known() && it!=last.elem->getSubscript().end(); it++) {
        if (t.kind == TypeKindE::String) {
            m_ctxt->addErrorMarker(last.id->getLocation(),
                "a sub-string of '%s' on the left of an assignment: the sub-string "
                "operator shall not be used there (LRM 7.6.2)",
                last.id->getId().c_str());
            return;
        }
        t = m_typer.subscript(t, it->get());
    }
}

void TaskCheckProcedural::checkForeachWrite(const LValue &lv, const char *what) {
    if (!lv.steps.size()) {
        return;
    }
    const PathStep &root = lv.steps.front();
    for (std::vector<Foreach>::const_reverse_iterator
            it=m_foreach.rbegin(); it!=m_foreach.rend(); it++) {
        if (root.decl && root.decl == it->idx) {
            m_ctxt->addErrorMarker(root.id->getLocation(),
                "foreach index variable '%s' is read-only and cannot be changed in "
                "the foreach body (LRM 20.7.8 g)", root.id->getId().c_str());
            return;
        }
        if (root.decl && root.decl == it->it) {
            // The iterator "is an alias to the collection element" (20.7.8 c):
            // a member or element of it written is the collection's element
            // written, which Example 291 shows is legal. Only the variable
            // itself, written whole, is.
            if (lv.steps.size() > 1 || hasSubscript(root.elem)) {
                continue;
            }
            m_ctxt->addErrorMarker(root.id->getLocation(),
                "foreach iterator variable '%s' is read-only and cannot be changed "
                "in the foreach body (LRM 20.7.8 g)", root.id->getId().c_str());
            return;
        }

        // The collection: replaced whole, or what holds it assigned, or
        // changed by one of its methods. An element's value is not the
        // collection's "contents" in this sense: the LRM's own Example 291
        // assigns `dst[i]` in `foreach (dst[i])`. So a write to an element,
        // or to a member of one, is not reported.
        const LValue &coll = it->coll;
        if (!coll.valid || lv.steps.size() > coll.steps.size()) {
            continue;
        }
        bool same = true;
        for (uint32_t k=0; same && k<lv.steps.size(); k++) {
            if (!coll.steps.at(k).decl || coll.steps.at(k).decl != lv.steps.at(k).decl) {
                same = false;
            } else if (hasSubscript(lv.steps.at(k).elem)
                    && (k+1 == coll.steps.size()
                        || hasSubscript(coll.steps.at(k).elem))) {
                // An element of the collection itself, or a step past a
                // subscript on both sides, which may name another element.
                same = false;
            }
        }
        if (!same) {
            continue;
        }
        const PathStep &c_last = coll.steps.back();
        if (what) {
            m_ctxt->addErrorMarker(root.id->getLocation(),
                "'%s' is the collection this foreach iterates, so '%s' cannot change "
                "it in the foreach body (LRM 20.7.8 g)",
                c_last.id->getId().c_str(), what);
        } else {
            m_ctxt->addErrorMarker(root.id->getLocation(),
                "'%s' is the collection this foreach iterates, so it cannot be "
                "changed in the foreach body (LRM 20.7.8 g)",
                c_last.id->getId().c_str());
        }
        return;
    }
}

// ---------------------------------------------------------------------------
// Calls
// ---------------------------------------------------------------------------

void TaskCheckProcedural::visitExprRefPathContext(ast::IExprRefPathContext *i) {
    if (i->getHier_id() && i->getTarget()) {
        checkCalls(i->getHier_id()->getElems(),
            m_ctxt->resolveSymbolPathRef(i->getTarget()));
    }
    ast::VisitorBase::visitExprRefPathContext(i);
}

void TaskCheckProcedural::visitExprRefPathStaticRooted(ast::IExprRefPathStaticRooted *i) {
    if (i->getLeaf()) {
        checkCalls(i->getLeaf()->getElems(), 0);
    }
    ast::VisitorBase::visitExprRefPathStaticRooted(i);
}

/** The built-in collection methods that change the collection (7.9). */
static bool changesCollection(const std::string &name) {
    return name == "push_back" || name == "push_front" || name == "pop_back"
        || name == "pop_front" || name == "insert" || name == "delete"
        || name == "clear";
}

void TaskCheckProcedural::checkCalls(
        const std::vector<ast::IExprMemberPathElemUP>   &elems,
        ast::IScopeChild                                *first_decl) {
    for (uint32_t k=0; k<elems.size(); k++) {
        ast::IExprMemberPathElem *elem = elems.at(k).get();
        if (!elem->getParams()) {
            continue;
        }
        ast::IScopeChild *decl = elem->getId()->getDecl();
        if (!decl && k == 0) {
            decl = first_decl;
        }
        if (ast::ISymbolFunctionScope *fn = NodeKind::cast<ast::ISymbolFunctionScope>(decl)) {
            checkConstArgs(elem, fn);
            checkCallPlatform(elem, fn);
        }
        if (k > 0 && m_foreach.size() && changesCollection(elem->getId()->getId())) {
            LValue recv = lvalueOfElems(elems, k, first_decl);
            if (recv.valid && m_typer.typeOfDecl(recv.steps.back().decl).isCollection()) {
                std::string what = elem->getId()->getId() + "()";
                checkForeachWrite(recv, what.c_str());
            }
        }
        // Past a call, the path is a value's: nothing after it is a variable.
        return;
    }
}

void TaskCheckProcedural::checkConstArgs(
        ast::IExprMemberPathElem    *elem,
        ast::ISymbolFunctionScope   *fn) {
    // 20.2.3 applies to a function with a PSS body: only it has const
    // parameters (const "can be specified for native functions only").
    if (!fn->getPrototypes().size() || !TaskCheckCallArgs::isNative(fn)) {
        return;
    }
    ast::IFunctionPrototype *proto = fn->getPrototypes().front();
    const std::vector<ast::IExprUP> &args = elem->getParams()->getParameters();
    const std::vector<ast::IFunctionParamDeclUP> &params = proto->getParameters();
    for (uint32_t ii=0; ii<args.size() && ii<params.size(); ii++) {
        ast::IFunctionParamDecl *p = params.at(ii).get();
        if (p->getIs_const() || p->getIs_varargs()) {
            continue;
        }
        bool aggregate = (p->getKind() == ast::FunctionParamDeclKind::ParamKind_Struct)
            || (p->getKind() == ast::FunctionParamDeclKind::ParamKind_DataType
                && m_typer.typeOfDataType(p->getType()).isAggregate());
        if (!aggregate) {
            // A scalar is passed by value: the callee cannot reach the caller's.
            continue;
        }
        LValue lv = lvalueOf(args.at(ii).get());
        int32_t k = (lv.valid) ? constStep(lv) : -1;
        if (k < 0) {
            continue;
        }
        const PathStep &step = lv.steps.at(k);
        m_ctxt->addErrorMarker(elem->getId()->getLocation(),
            "argument %d of '%s' is %s '%s', so parameter '%s' must be declared "
            "const (LRM 20.2.3)",
            ii+1,
            elem->getId()->getId().c_str(),
            (NodeKind::cast<ast::IFunctionParamDecl>(step.decl))
                ? "const parameter" : "constant",
            step.id->getId().c_str(),
            p->getName() ? p->getName()->getId().c_str() : "?");
    }
}

}
