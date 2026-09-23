/*
 * TaskCheckPackedStructs.cpp
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
#include "TaskCheckPackedStructs.h"


namespace pssp {


TaskCheckPackedStructs::TaskCheckPackedStructs(ResolveContext *ctxt) :
        m_ctxt(ctxt), m_classifier(ctxt->getFactory(), ctxt->root()) {
    DEBUG_INIT("pssp::TaskCheckPackedStructs", ctxt->getDebugMgr());
}

TaskCheckPackedStructs::~TaskCheckPackedStructs() {

}

void TaskCheckPackedStructs::check(ast::IRootSymbolScope *root) {
    DEBUG_ENTER("check");
    m_reported.clear();
    walk(root);
    DEBUG_LEAVE("check");
}

void TaskCheckPackedStructs::walk(ast::ISymbolScope *s) {
    // Symbol scopes only: packages, components and types, where a struct can
    // be declared. The AST under them -- exec bodies, constraints -- declares
    // no types, and is not walked.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=s->getChildren().begin();
        it!=s->getChildren().end(); it++) {
        if (ast::ISymbolTypeScope *ts =
                dynamic_cast<ast::ISymbolTypeScope *>(it->get())) {
            checkTypeScope(ts);
        } else if (ast::ISymbolScope *cs =
                dynamic_cast<ast::ISymbolScope *>(it->get())) {
            walk(cs);
        }
    }
}

void TaskCheckPackedStructs::checkTypeScope(ast::ISymbolTypeScope *s) {
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(s->getTarget());

    // Types nested in this one (a struct declared in a component).
    walk(s);

    if (!ts) {
        return;
    }

    // The core library is not checked: sized_addr_handle_s is the spec's own
    // exception to the member rules (R10), and nothing else there is at
    // fault in a user's model.
    if (ts->getLocation().fileid <= 0) {
        return;
    }

    if (ts->getParams() && !ts->getParams()->getSpecialized()) {
        // A generic. Its members are checked per specialization, where they
        // have types. Whether it is packed is only answerable through a
        // specialization too -- its super type is not resolved on the
        // generic itself.
        bool packed = false;
        for (std::vector<ast::ISymbolTypeScopeUP>::const_iterator
            it=s->getSpec_types().begin();
            it!=s->getSpec_types().end(); it++) {
            checkTypeScope(it->get());
            packed |= m_classifier.isPackedStruct(it->get());
        }

        // An extension's members are merged into the generic's scope, and
        // copied into each specialization from there. Only the generic's
        // copies are recorded as extension-contributed.
        if (packed) {
            checkExtensionFields(s);
        }
        return;
    }

    if (!m_classifier.isPackedStruct(s)) {
        return;
    }

    checkMembers(s);
    checkExtensionFields(s);
}

void TaskCheckPackedStructs::checkMembers(ast::ISymbolTypeScope *s) {
    DEBUG_ENTER("checkMembers %s", s->getName().c_str());
    // This struct's own fields. Inherited ones are checked where they are
    // declared -- a base struct is packed too, or this one would not be.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=s->getChildren().begin();
        it!=s->getChildren().end(); it++) {
        ast::IField *f = dynamic_cast<ast::IField *>(it->get());
        if (!f) {
            continue;
        }

        // A static member is not part of the layout (Q1).
        if ((f->getAttr() & ast::FieldAttr::Static) != ast::FieldAttr::NoFlags) {
            continue;
        }

        // A field an extension added is reported as that (PSS013). Its type
        // is beside the point.
        if (m_ctxt->extensionDeclScope(f)) {
            continue;
        }

        PackableInfo info = m_classifier.classifyMember(s, f->getType());

        // A packed struct whose own member is at fault: that member is
        // reported where it is declared, not again at every use.
        if (info.kind != PackableInfo::NotPackable || info.nested) {
            continue;
        }

        // One short line; `--describe PSS012` carries the rule itself.
        std::string msg = "field '" + f->getName()->getId()
            + "' of packed struct '" + typeName(s) + "' is " + info.why
            + (info.hint.size()?("; " + info.hint):", which cannot be packed");

        const ast::Location &loc = (f->getType() && f->getType()->getLocation().lineno > 0)?
            f->getType()->getLocation():f->getLocation();
        report(loc, msg, info.culprit, "declared here");
    }
    DEBUG_LEAVE("checkMembers %s", s->getName().c_str());
}

void TaskCheckPackedStructs::checkExtensionFields(ast::ISymbolTypeScope *s) {
    // 21.13.1: "Type extensions of packed structs shall not add new fields."
    // Constraints, exec blocks and the like are fine; only fields are ruled
    // out. A static member is not a field of the layout (Q1), so an
    // extension may add one.
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=s->getChildren().begin();
        it!=s->getChildren().end(); it++) {
        ast::IField *f = dynamic_cast<ast::IField *>(it->get());
        if (!f || !m_ctxt->extensionDeclScope(f)) {
            continue;
        }
        if ((f->getAttr() & ast::FieldAttr::Static) != ast::FieldAttr::NoFlags) {
            continue;
        }
        report(
            f->getLocation(),
            "type extension of packed struct '" + typeName(s) + "' adds field '"
                + f->getName()->getId() + "'; an extension of a packed struct "
                "may not add fields",
            s->getTarget(),
            "packed struct declared here");
    }
}

void TaskCheckPackedStructs::report(
        const ast::Location     &loc,
        const std::string       &msg,
        ast::IScopeChild        *related,
        const std::string       &related_label) {
    if (!m_reported.insert(std::make_tuple(
            loc.fileid, loc.lineno, loc.linepos, msg)).second) {
        return;
    }
    std::vector<std::pair<ast::Location, std::string>> rel;
    if (related && related->getLocation().lineno > 0
            && related->getLocation().fileid > 0) {
        rel.push_back(std::make_pair(related->getLocation(), related_label));
    }
    m_ctxt->addMarker(MarkerSeverityE::Error, loc, msg, rel);
}

std::string TaskCheckPackedStructs::typeName(ast::ISymbolTypeScope *s) {
    ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(s->getTarget());
    return (ts && ts->getName())?ts->getName()->getId():s->getName();
}

dmgr::IDebug *TaskCheckPackedStructs::m_dbg = 0;

}
