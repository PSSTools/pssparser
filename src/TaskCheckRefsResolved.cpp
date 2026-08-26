/**
 * TaskCheckRefsResolved.cpp
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
 *
 * Created on:
 *     Author:
 */
#include "dmgr/impl/DebugMacros.h"
#include "TaskCheckRefsResolved.h"
#include "pssp/ast/ITypeScope.h"

namespace pssp {

TaskCheckRefsResolved::TaskCheckRefsResolved(ResolveContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskCheckRefsResolved", ctxt->getDebugMgr());
}

TaskCheckRefsResolved::~TaskCheckRefsResolved() { }

/**
 * Sweeps the whole tree for template parameter *declarations*.
 *
 * `struct S <int SIZE, struct T : base_s> { T item; }` puts `T` in the body as
 * an ordinary user-defined type reference that binds to nothing until the
 * generic is specialized -- and a generic that is never instantiated is still
 * legal, so it never binds at all. Skipping unspecialized generics by walking
 * around them was tried first and missed several shapes (a generic nested in a
 * component, a specialization reached through its declaration); collecting the
 * names is insensitive to how the walk gets there, which is the property this
 * needs.
 *
 * The exemption is by name and therefore model-wide: a type genuinely named
 * `T` somewhere else would not be reported. That is the conservative direction
 * -- this check must not fire on valid code -- and it is why the exemption is
 * a declared-parameter set rather than a hardcoded list of short names.
 */
class TaskCheckRefsResolved::ParamNameCollector : public ast::VisitorBase {
public:
    ParamNameCollector(
        std::set<std::string> &param_names,
        std::set<std::string> &type_names) :
        m_param_names(param_names), m_type_names(type_names) { }

    virtual void visitTemplateParamDeclList(ast::ITemplateParamDeclList *i) override {
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=i->getParams().begin();
            it!=i->getParams().end(); it++) {
            if ((*it)->getName()) {
                m_param_names.insert((*it)->getName()->getId());
            }
        }
        ast::VisitorBase::visitTemplateParamDeclList(i);
    }

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override {
        m_type_names.insert(i->getName());
        ast::VisitorBase::visitSymbolTypeScope(i);
    }

private:
    std::set<std::string>   &m_param_names;
    std::set<std::string>   &m_type_names;
};

void TaskCheckRefsResolved::check(
        ast::IRootSymbolScope   *root,
        uint32_t                n_builtin_units) {
    DEBUG_ENTER("check");
    m_visited.clear();
    m_param_names.clear();
    m_type_names.clear();

    ParamNameCollector collector(m_param_names, m_type_names);
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=root->getChildren().begin();
        it!=root->getChildren().end(); it++) {
        it->get()->accept(&collector);
    }

    // The symbol tree's children, not root->getUnits(): the units hold the
    // same nodes reached through the scopes, and walking both reports every
    // finding twice.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=root->getChildren().begin();
        it!=root->getChildren().end(); it++) {
        it->get()->accept(m_this);
    }

    DEBUG_LEAVE("check");
}

void TaskCheckRefsResolved::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
    ast::ITypeScope *i_ts = dynamic_cast<ast::ITypeScope *>(i->getTarget());

    // An unspecialized generic's body names its own template parameters
    // (`TRAIT`, `Tc`, `Te`), which are parameters rather than types and never
    // bind to one. Its specializations are checked instead -- those have their
    // arguments substituted, so a reference left unresolved in one is a real
    // finding. TaskResolveSuperTypes skips the same shape for the same reason.
    if (i_ts && i_ts->getParams() && !i_ts->getParams()->getSpecialized()) {
        DEBUG("Note: skipping unspecialized templated type %s",
            i->getName().c_str());
        return;
    }

    ast::VisitorBase::visitSymbolTypeScope(i);
}

void TaskCheckRefsResolved::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
    if (!i->getType_id()) {
        return;
    }

    if (i->getType_id()->getTarget()) {
        // Bound. Nothing further to say.
        return;
    }

    // The bundled core library is a known-incomplete subset (see
    // pssparser-issues.md 4), so its own unresolved references would fire on
    // every run of every model and train users to ignore this check. A user
    // reference *to* a missing stdlib symbol is still reported: that reference
    // lives in a user unit.
    const ast::Location &loc = i->getLocation();
    if (loc.fileid <= 0) {
        return;
    }

    // One report per node. The same AST node is reachable through more than
    // one scope once extensions have been applied.
    if (!m_visited.insert(i).second) {
        return;
    }

    // The usual case: the reference failed to resolve and *was* diagnosed,
    // with a better message than this one can give ("unknown type 'x'; did you
    // mean 'y'?"). Repeating it here would turn one mistake into two errors.
    // This check exists for the references that reach the end unbound with
    // nothing said about them at all -- that is the silent drop, and it is what
    // is left after this filter.
    if (m_ctxt->wasReported(loc)) {
        DEBUG("Note: already reported at %d:%d", loc.lineno, loc.linepos);
        return;
    }

    std::string name;
    if (i->getType_id()->getElems().size()) {
        for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
            it=i->getType_id()->getElems().begin();
            it!=i->getType_id()->getElems().end(); it++) {
            if (it != i->getType_id()->getElems().begin()) {
                name += "::";
            }
            name += (*it)->getId()->getId();
        }
    }

    if (name.empty()) {
        name = "<unnamed>";
    }

    const std::string &last = i->getType_id()->getElems().back()->getId()->getId();

    // A template parameter used as a type inside its own generic's body binds
    // only when that generic is specialized -- and a generic nothing
    // instantiates never binds at all, legally. See ParamNameCollector.
    if (i->getType_id()->getElems().size() == 1
            && m_param_names.find(name) != m_param_names.end()) {
        DEBUG("Note: '%s' names a template parameter", name.c_str());
        return;
    }

    // A qualified reference whose last element names a type the model declares
    // is left alone, even though this node's target is null.
    //
    // `tx::send_pkt s;` in an activity is the case that matters: `tx` is a
    // component *instance*, not a package, so the path is resolved by instance
    // rather than by scope and this node never receives a target. It is legal
    // PSS and pssc resolves it (targets/sv/context.py does the same
    // last-segment lookup). Reporting it would reject working models -- which
    // is the failure mode that gets a check switched off, and worth more than
    // the recall lost: `p::nosuch_s`, the reference this check was added for,
    // names nothing declared anywhere and is still reported.
    if (i->getType_id()->getElems().size() > 1
            && m_type_names.find(last) != m_type_names.end()) {
        DEBUG("Note: '%s' ends in a declared type name", name.c_str());
        return;
    }

    m_ctxt->addMarker(
        MarkerSeverityE::Error,
        loc,
        "type '%s' is never resolved: the reference is left unbound after "
        "linking, so anything reading this model sees a field with no type",
        name.c_str());
}

dmgr::IDebug *TaskCheckRefsResolved::m_dbg = 0;

}
