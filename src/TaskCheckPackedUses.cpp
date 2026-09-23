/*
 * TaskCheckPackedUses.cpp
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
#include <memory>
#include "dmgr/impl/DebugMacros.h"
#include "TaskCheckPackedUses.h"


namespace pssp {


TaskCheckPackedUses::TaskCheckPackedUses(ResolveContext *ctxt) :
        m_ctxt(ctxt),
        m_classifier(ctxt->getFactory(), ctxt->root()),
        m_resolver(ctxt->getDebugMgr(), ctxt->root()) {
    DEBUG_INIT("pssp::TaskCheckPackedUses", ctxt->getDebugMgr());
}

TaskCheckPackedUses::~TaskCheckPackedUses() {

}

void TaskCheckPackedUses::check(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("check");
    m_visited.clear();
    m_reported.clear();
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=root->getChildren().begin();
        it!=root->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }
    DEBUG_LEAVE("check");
}

void TaskCheckPackedUses::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());

    // A generic's body is checked through its specializations, where the
    // arguments are bound. The body itself names parameters, not types.
    if (ts && ts->getParams() && !ts->getParams()->getSpecialized()) {
        for (std::vector<ast::ISymbolTypeScopeUP>::const_iterator
            it=i->getSpec_types().begin();
            it!=i->getSpec_types().end(); it++) {
            (*it)->accept(m_this);
        }
        return;
    }

    ast::VisitorBase::visitSymbolTypeScope(i);
}

void TaskCheckPackedUses::visitTypeScope(ast::ITypeScope *i) {
    // The generic's AST is also reachable as a child of the enclosing
    // scope's AST. Same rule by that route.
    if (i->getParams() && !i->getParams()->getSpecialized()) {
        return;
    }
    ast::VisitorBase::visitTypeScope(i);
}

void TaskCheckPackedUses::visitTypeIdentifier(ast::ITypeIdentifier *i) {
    if (!m_visited.insert(i).second) {
        return;
    }

    if (i->getTarget() && i->getElems().size()) {
        ast::ISymbolTypeScope *spec = dynamic_cast<ast::ISymbolTypeScope *>(
            m_resolver.resolve(i->getTarget()));
        if (spec) {
            // An expression carries no position of its own; its first
            // identifier does.
            const ast::Location &loc = i->getElems().front()->getId()->getLocation();
            checkUse(spec, loc);
        }
    }

    ast::VisitorBase::visitTypeIdentifier(i);
}

void TaskCheckPackedUses::visitExprRefPathStatic(ast::IExprRefPathStatic *i) {
    if (!m_visited.insert(i).second) {
        return;
    }

    // `sizeof_s<T>::nbits` resolves to the member. The specialization is the
    // path up to and including its last TypeSpec step.
    if (i->getTarget() && i->getBase().size()) {
        const std::vector<ast::SymbolRefPathElem> &path = i->getTarget()->getPath();
        int32_t last = -1;
        for (uint32_t k=0; k<path.size(); k++) {
            if (path.at(k).kind == ast::SymbolRefPathElemKind::ElemKind_TypeSpec) {
                last = k;
            }
        }
        if (last >= 0) {
            std::unique_ptr<ast::ISymbolRefPath> spec_p(
                m_ctxt->getFactory()->getAstFactory()->mkSymbolRefPath());
            spec_p->getPath().insert(
                spec_p->getPath().begin(),
                path.begin(), path.begin()+last+1);
            ast::ISymbolTypeScope *spec = dynamic_cast<ast::ISymbolTypeScope *>(
                m_resolver.resolve(spec_p.get()));
            if (spec) {
                const ast::Location &loc =
                    i->getBase().front()->getId()->getLocation();
                checkUse(spec, loc);
            }
        }
    }

    ast::VisitorBase::visitExprRefPathStatic(i);
}

void TaskCheckPackedUses::checkUse(
        ast::ISymbolTypeScope   *spec,
        const ast::Location     &loc) {
    // Only uses in the user's model. The core library's own references --
    // reg_c's `sizeof_s<R>` -- are to its parameters.
    if (loc.fileid <= 0) {
        return;
    }
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(spec->getTarget());
    if (!ts || !ts->getParams() || !ts->getParams()->getSpecialized()) {
        return;
    }
    if (TaskClassifyPackable::isCoreLibStruct(spec, "sizeof_s")) {
        checkSizeof(ts, loc);
    } else if (TaskClassifyPackable::isCoreLibStruct(spec, "reg_c")) {
        checkReg(ts, loc);
    }
}

void TaskCheckPackedUses::checkSizeof(
        ast::ITypeScope         *spec,
        const ast::Location     &loc) {
    PackableInfo info = m_classifier.classify(typeParam(spec, "T"));

    // A packed struct whose own member is at fault is reported at the member
    // (PSS012); the struct is a legal argument in itself.
    if (info.kind != PackableInfo::NotPackable || info.nested) {
        return;
    }

    report(MarkerSeverityE::Error, loc,
        "sizeof_s argument is " + info.why
            + (info.hint.size()?("; " + info.hint):", which has no packed size"),
        info.culprit);
}

void TaskCheckPackedUses::checkReg(
        ast::ITypeScope         *spec,
        const ast::Location     &loc) {
    ast::IDataType *r_t = typeParam(spec, "R");
    PackableInfo info = m_classifier.classify(r_t);

    if (info.kind == PackableInfo::NotPackable) {
        if (!info.nested) {
            // Q3: any R whose size can be established is accepted -- a
            // packed struct, bit[N], int[32], an enum with a base type.
            report(MarkerSeverityE::Error, loc,
                "reg_c value type is " + info.why
                    + (info.hint.size()?("; " + info.hint):", which has no packed size"),
                info.culprit);
        }
        return;
    }
    if (info.kind != PackableInfo::Ok) {
        return;
    }

    // SZ is the user's argument, or the default (8*sizeof_s<R>::nbytes),
    // which folds once sizeof_s is sized. If it does not fold there is
    // nothing to compare.
    int64_t sz;
    if (!m_classifier.valueParam(spec, "SZ", sz)) {
        DEBUG("SZ does not fold");
        return;
    }

    std::string r_desc = typeDesc(r_t);
    char tmp[256];
    if (sz < info.bits) {
        snprintf(tmp, sizeof(tmp),
            "reg_c width SZ = %lld is smaller than its value type%s (%lld bits)",
            (long long)sz,
            r_desc.size()?(" " + r_desc).c_str():"",
            (long long)info.bits);
        report(MarkerSeverityE::Error, loc, tmp, info.culprit);
    } else if (sz != 8 && sz != 16 && sz != 32 && sz != 64) {
        // Not a "shall", so a warning: the spec's translation of register
        // access (21.14.5a) picks readN/writeN by the register's size, and
        // those exist only for 8, 16, 32 and 64 bits (21.13.9).
        snprintf(tmp, sizeof(tmp),
            "reg_c width SZ = %lld has no primitive access function; use 8, 16, "
            "32 or 64 bits",
            (long long)sz);
        report(MarkerSeverityE::Warn, loc, tmp, 0);
    }
}

ast::IDataType *TaskCheckPackedUses::typeParam(
        ast::ITypeScope     *spec,
        const char          *name) {
    for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
        it=spec->getParams()->getParams().begin();
        it!=spec->getParams()->getParams().end(); it++) {
        ast::ITemplateGenericTypeParamDecl *tp =
            dynamic_cast<ast::ITemplateGenericTypeParamDecl *>(it->get());
        if (tp && tp->getName() && tp->getName()->getId() == name) {
            return tp->getDflt();
        }
    }
    return 0;
}

void TaskCheckPackedUses::report(
        MarkerSeverityE         severity,
        const ast::Location     &loc,
        const std::string       &msg,
        ast::IScopeChild        *related) {
    if (!m_reported.insert(std::make_tuple(
            loc.fileid, loc.lineno, loc.linepos, msg)).second) {
        return;
    }
    std::vector<std::pair<ast::Location, std::string>> rel;
    if (related && related->getLocation().lineno > 0
            && related->getLocation().fileid > 0) {
        rel.push_back(std::make_pair(related->getLocation(), "declared here"));
    }
    m_ctxt->addMarker(severity, loc, msg, rel);
}

std::string TaskCheckPackedUses::typeDesc(ast::IDataType *t) {
    ast::IDataTypeUserDefined *ut = dynamic_cast<ast::IDataTypeUserDefined *>(t);
    if (ut && ut->getType_id() && ut->getType_id()->getElems().size()) {
        return "'" + ut->getType_id()->getElems().back()->getId()->getId() + "'";
    }
    return "";
}

dmgr::IDebug *TaskCheckPackedUses::m_dbg = 0;

}
