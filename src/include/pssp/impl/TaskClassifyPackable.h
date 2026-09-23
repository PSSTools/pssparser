/**
 * TaskClassifyPackable.h
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
#pragma once
#include <memory>
#include <set>
#include <string>
#include "dmgr/IDebugMgr.h"
#include "dmgr/impl/DebugMacros.h"
#include "pssp/IFactory.h"
#include "pssp/IValInt.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/impl/BuiltinCollectionUtil.h"
#include "pssp/impl/TaskEvalExpr.h"
#include "pssp/impl/TaskResolveSymbolPathRef.h"

namespace pssp {

/**
 * What 21.13.1 says about one type as a member of a packed struct.
 *
 * ``Ok`` carries the packed width. ``NotPackable`` means the spec rules the
 * type out. ``why`` is a noun phrase naming it ("a string", "enum 'e', which
 * has no base type"), ``hint`` says how to fix it when there is something
 * specific to say, and ``culprit`` is the declaration to point at, if any.
 * Both end up in a one-line diagnostic, so keep them short: the rule itself
 * is in the marker's --describe text.
 * ``Incomplete`` means the answer is not known -- an unresolved reference, an
 * unspecialized template parameter, a width that does not fold -- and is
 * never a reason to report anything.
 */
struct PackableInfo {
    enum Kind { Ok, NotPackable, Incomplete };

    Kind                kind;
    int64_t             bits;
    std::string         why;
    std::string         hint;
    ast::IScopeChild    *culprit;

    // True when the offending type is a packed struct whose own member is at
    // fault. The member is reported where it is declared; a field of that
    // struct's type is not reported a second time.
    bool                nested;

    PackableInfo() : kind(Incomplete), bits(0), culprit(0), nested(false) { }

    static PackableInfo ok(int64_t bits) {
        PackableInfo r; r.kind = Ok; r.bits = bits; return r;
    }
    static PackableInfo notPackable(
            const std::string   &why,
            ast::IScopeChild    *culprit=0,
            const std::string   &hint="") {
        PackableInfo r; r.kind = NotPackable; r.why = why; r.culprit = culprit;
        r.hint = hint;
        return r;
    }
    static PackableInfo incomplete(const std::string &why) {
        PackableInfo r; r.kind = Incomplete; r.why = why; return r;
    }
};

/**
 * The one packability predicate and packed-size function (21.13.1, 21.13.2).
 *
 * ``sizeof_s``, the packed-struct member check and the register checks all
 * ask this; none of them computes a size or a legality answer of its own.
 * That is what keeps them consistent with each other -- a type ``sizeof_s``
 * sizes is exactly a type a packed struct may contain.
 *
 * See docs/design/packed-struct-checks-plan.md, sections 1 and 3.1.
 */
class TaskClassifyPackable : public virtual ast::VisitorBase {
public:

    TaskClassifyPackable(
        IFactory                *factory,
        ast::ISymbolScope       *root) :
            m_dbg(0), m_factory(factory), m_root(root),
            m_resolver(factory->getDebugMgr(), root) {
        DEBUG_INIT("pssp::TaskClassifyPackable", factory->getDebugMgr());
    }

    virtual ~TaskClassifyPackable() { }

    /**
     * Classify a data type as it appears in a member declaration or as the
     * argument of ``sizeof_s``/``reg_c``.
     */
    PackableInfo classify(ast::IDataType *t) {
        if (!t) {
            return PackableInfo::incomplete("no type");
        }
        PackableInfo save = m_info;
        m_info = PackableInfo::incomplete("unsupported type");
        t->accept(m_this);
        PackableInfo ret = m_info;
        m_info = save;
        return ret;
    }

    /**
     * Classify whatever a type reference resolved to: a type scope, an enum
     * scope, a typedef, or a template parameter.
     */
    PackableInfo classifySymbol(ast::IScopeChild *c) {
        if (!c) {
            return PackableInfo::incomplete("unresolved type");
        }
        if (ast::ISymbolTypeScope *ts = dynamic_cast<ast::ISymbolTypeScope *>(c)) {
            return classifyTypeScope(ts);
        }
        if (ast::ISymbolEnumScope *es = dynamic_cast<ast::ISymbolEnumScope *>(c)) {
            return classifyEnum(es);
        }
        if (ast::ITypedefDeclaration *td = dynamic_cast<ast::ITypedefDeclaration *>(c)) {
            return classify(td->getType());
        }
        // A member typed by a template parameter (`T v;`) resolves to the
        // parameter's declaration. In a specialization that declaration's
        // `dflt` holds the bound argument; in the generic it holds only the
        // declared default, which says nothing about any use -- so follow it
        // only for parameter lists known to be bound (see bindParams).
        if (m_bound.find(c) != m_bound.end()) {
            if (ast::ITemplateGenericTypeParamDecl *tp =
                    dynamic_cast<ast::ITemplateGenericTypeParamDecl *>(c)) {
                return classify(tp->getDflt());
            }
            if (ast::ITemplateCategoryTypeParamDecl *tp =
                    dynamic_cast<ast::ITemplateCategoryTypeParamDecl *>(c)) {
                return classify(tp->getDflt());
            }
        }
        // A template parameter (inside an unspecialized generic), or
        // something this function does not know how to size: no answer,
        // rather than a guess.
        return PackableInfo::incomplete("not a sizable type");
    }

    /**
     * Classify the type of a member of ``owner``. A member typed by one of
     * ``owner``'s bound template parameters is classified by its argument.
     */
    PackableInfo classifyMember(ast::ISymbolTypeScope *owner, ast::IDataType *t) {
        std::set<ast::IScopeChild *> save = m_bound;
        bindParams(owner);
        PackableInfo ret = classify(t);
        m_bound = save;
        return ret;
    }

    /**
     * True for a struct derived, directly or indirectly, from
     * ``std_pkg::packed_s`` (R1), and whose own kind is ``struct`` -- a flow
     * or resource object inheriting from a packed struct is not packed
     * (17.1, R2).
     */
    bool isPackedStruct(ast::ISymbolTypeScope *s) {
        ast::IStruct *st = s?dynamic_cast<ast::IStruct *>(s->getTarget()):0;
        if (!st || st->getKind() != ast::StructKind::Struct) {
            return false;
        }
        return derivesFromPackedS(s);
    }

    /**
     * The instance fields a packed struct lays out, base struct first
     * (21.13.1.1). ``static`` members are not part of the layout (Q1).
     */
    void packedFields(
            ast::ISymbolTypeScope           *s,
            std::vector<ast::IField *>      &fields) {
        std::set<ast::ISymbolTypeScope *> seen;
        collectFields(s, fields, seen);
    }

    /**
     * True when ``s`` is (a specialization of) the named core-library struct.
     * The core library is recognized by where it is declared -- the bundled
     * files, fileid <= 0 -- not by name alone, since a user may declare a
     * ``packed_s`` of their own.
     */
    static bool isCoreLibStruct(ast::ISymbolTypeScope *s, const char *name) {
        ast::ITypeScope *ts = s?dynamic_cast<ast::ITypeScope *>(s->getTarget()):0;
        return ts && ts->getName() && ts->getName()->getId() == name
            && ts->getLocation().fileid <= 0;
    }

    /**
     * Fold an integer expression, or return false. Widths, array sizes and
     * template value arguments go through here.
     */
    bool evalInt(ast::IExpr *e, int64_t &val) {
        if (!e) {
            return false;
        }
        std::unique_ptr<IVal> v(TaskEvalExpr(m_factory, m_root).eval(e));
        IValInt *vi = dynamic_cast<IValInt *>(v.get());
        if (!vi) {
            return false;
        }
        val = vi->getValS();
        return true;
    }

    /**
     * A bound value parameter of a specialization, by name.
     */
    bool valueParam(ast::ITypeScope *ts, const char *name, int64_t &val) {
        if (!ts || !ts->getParams()) {
            return false;
        }
        for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
            it=ts->getParams()->getParams().begin();
            it!=ts->getParams()->getParams().end(); it++) {
            ast::ITemplateValueParamDecl *vp =
                dynamic_cast<ast::ITemplateValueParamDecl *>(it->get());
            if (vp && vp->getName() && vp->getName()->getId() == name) {
                return evalInt(vp->getDflt(), val);
            }
        }
        return false;
    }

    // ---------------------------------------------------------------- types

    virtual void visitDataTypeBool(ast::IDataTypeBool *i) override {
        // 21.13.1.1: "Boolean fields are considered to be of 1 bit."
        m_info = PackableInfo::ok(1);
    }

    virtual void visitDataTypeInt(ast::IDataTypeInt *i) override {
        int64_t w;
        if (evalInt(i->getWidth(), w)) {
            m_info = PackableInfo::ok(w);
        } else {
            m_info = PackableInfo::incomplete("width does not fold");
        }
    }

    virtual void visitDataTypeFloat(ast::IDataTypeFloat *i) override {
        m_info = PackableInfo::ok(i->getIs_float64()?64:32);
    }

    virtual void visitDataTypeChandle(ast::IDataTypeChandle *i) override {
        // addr_handle_t is a chandle, and an address is the usual reason for
        // wanting one here (21.13.3.1).
        m_info = PackableInfo::notPackable("a chandle", 0,
            "use sized_addr_handle_s<SZ> for an address");
    }

    virtual void visitDataTypeString(ast::IDataTypeString *i) override {
        m_info = PackableInfo::notPackable("a string");
    }

    virtual void visitDataTypeRef(ast::IDataTypeRef *i) override {
        m_info = PackableInfo::notPackable("a reference");
    }

    virtual void visitDataTypePyObj(ast::IDataTypePyObj *i) override {
        m_info = PackableInfo::notPackable("a pyobj");
    }

    virtual void visitDataTypeEnum(ast::IDataTypeEnum *i) override {
        if (i->getTid()) {
            i->getTid()->accept(m_this);
        }
    }

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override {
        ast::ITypeIdentifier *tid = i->getType_id();
        if (!tid || !tid->getTarget()) {
            m_info = PackableInfo::incomplete("unresolved type");
            return;
        }
        m_info = classifySymbol(m_resolver.resolve(tid->getTarget()));
    }

private:

    PackableInfo classifyEnum(ast::ISymbolEnumScope *es) {
        ast::IEnumDecl *decl = es->getDecl();
        if (!decl) {
            return PackableInfo::incomplete("enum declaration not found");
        }
        if (!decl->getBase_type()) {
            // R5: "enumerated types that have a base type". An enum without
            // one has no defined representation, so it has no packed width.
            return PackableInfo::notPackable(
                "enum '" + es->getName() + "', which has no base type", decl,
                "declare it as 'enum " + es->getName() + " : bit[N]'");
        }
        PackableInfo r = classify(decl->getBase_type());
        return r;
    }

    PackableInfo classifyTypeScope(ast::ISymbolTypeScope *s) {
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(s->getTarget());
        if (!ts) {
            return PackableInfo::incomplete("not a type");
        }

        // An unspecialized generic has no bound arguments to size it with.
        if (ts->getParams() && !ts->getParams()->getSpecialized()) {
            return PackableInfo::incomplete("unspecialized generic");
        }

        switch (builtinCollectionKind(ts)) {
            case CollectionKind::Array: return classifyArray(ts);
            case CollectionKind::List:  return notACollection("a list");
            case CollectionKind::Set:   return notACollection("a set");
            case CollectionKind::Map:   return notACollection("a map");
            default: break;
        }

        ast::IStruct *st = dynamic_cast<ast::IStruct *>(ts);
        std::string name = ts->getName()?ts->getName()->getId():s->getName();
        if (!st) {
            return PackableInfo::notPackable("'" + name + "'", ts,
                "it is not a data type");
        }

        if (st->getKind() != ast::StructKind::Struct) {
            // 17.1: inheriting from a packed struct does not make a flow or
            // resource object packed.
            return PackableInfo::notPackable(
                std::string(kindName(st->getKind())) + " '" + name + "'", ts,
                std::string("a ") + kindName(st->getKind()) + " is never "
                "packed, even when it inherits from a packed struct");
        }

        // R10: the core library's own special case. Its packed width is SZ;
        // the chandle inside it is the handle's representation, not a field.
        if (isCoreLibStruct(s, "sized_addr_handle_s")) {
            int64_t sz;
            if (valueParam(ts, "SZ", sz)) {
                return PackableInfo::ok(sz);
            }
            return PackableInfo::incomplete("SZ does not fold");
        }

        if (!derivesFromPackedS(s)) {
            return PackableInfo::notPackable(
                "struct '" + name + "', which is not packed", ts,
                "derive it from packed_s<>");
        }

        return sizeStruct(s);
    }

    PackableInfo classifyArray(ast::ITypeScope *ts) {
        const std::vector<ast::ITemplateParamDeclUP> &params =
            ts->getParams()->getParams();
        if (params.size() < 2) {
            return PackableInfo::incomplete("malformed array");
        }
        ast::ITemplateGenericTypeParamDecl *tp =
            dynamic_cast<ast::ITemplateGenericTypeParamDecl *>(params.at(0).get());
        ast::ITemplateValueParamDecl *np =
            dynamic_cast<ast::ITemplateValueParamDecl *>(params.at(1).get());
        if (!tp || !np) {
            return PackableInfo::incomplete("malformed array");
        }
        PackableInfo elem = classify(tp->getDflt());
        if (elem.kind == PackableInfo::NotPackable && !elem.nested) {
            elem.why = "an array of " + elem.why;
        }
        if (elem.kind != PackableInfo::Ok) {
            return elem;
        }
        int64_t n;
        if (!evalInt(np->getDflt(), n)) {
            return PackableInfo::incomplete("array size does not fold");
        }
        return PackableInfo::ok(elem.bits * n);
    }

    PackableInfo sizeStruct(ast::ISymbolTypeScope *s) {
        if (!m_active.insert(s).second) {
            // A struct that contains itself. The cycle is reported elsewhere.
            return PackableInfo::incomplete("recursive struct");
        }

        std::vector<ast::IField *> fields;
        packedFields(s, fields);

        std::set<ast::IScopeChild *> save = m_bound;
        bindParams(s);

        PackableInfo ret = PackableInfo::ok(0);
        for (std::vector<ast::IField *>::const_iterator
            it=fields.begin(); it!=fields.end(); it++) {
            PackableInfo f = classify((*it)->getType());
            if (f.kind == PackableInfo::NotPackable) {
                // The member is reported at its own declaration; a field of
                // this struct's type is not the place to report it again.
                ret = f;
                ret.nested = true;
                break;
            } else if (f.kind == PackableInfo::Incomplete) {
                // Keep looking: a NotPackable member later on still decides
                // the answer.
                ret = f;
            } else if (ret.kind == PackableInfo::Ok) {
                ret.bits += f.bits;
            }
        }

        m_bound = save;
        m_active.erase(s);
        return ret;
    }

    /**
     * Mark the parameter declarations of ``s`` and of its base types as
     * bound, for each whose parameter list is a specialization's.
     */
    void bindParams(ast::ISymbolTypeScope *s) {
        std::set<ast::ISymbolTypeScope *> seen;
        while (s && seen.insert(s).second) {
            ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(s->getTarget());
            if (ts && ts->getParams() && ts->getParams()->getSpecialized()) {
                for (std::vector<ast::ITemplateParamDeclUP>::const_iterator
                    it=ts->getParams()->getParams().begin();
                    it!=ts->getParams()->getParams().end(); it++) {
                    m_bound.insert(it->get());
                }
            }
            s = superOf(s);
        }
    }

    bool derivesFromPackedS(ast::ISymbolTypeScope *s) {
        std::set<ast::ISymbolTypeScope *> seen;
        while (s && seen.insert(s).second) {
            if (isCoreLibStruct(s, "packed_s")) {
                return true;
            }
            s = superOf(s);
        }
        return false;
    }

    ast::ISymbolTypeScope *superOf(ast::ISymbolTypeScope *s) {
        ast::ITypeScope *ts = dynamic_cast<ast::ITypeScope *>(s->getTarget());
        if (!ts || !ts->getSuper_t() || !ts->getSuper_t()->getTarget()) {
            return 0;
        }
        return dynamic_cast<ast::ISymbolTypeScope *>(
            m_resolver.resolve(ts->getSuper_t()->getTarget()));
    }

    void collectFields(
            ast::ISymbolTypeScope               *s,
            std::vector<ast::IField *>          &fields,
            std::set<ast::ISymbolTypeScope *>   &seen) {
        if (!s || !seen.insert(s).second || isCoreLibStruct(s, "packed_s")) {
            return;
        }
        // Base first: fields of a derived struct are "considered to be
        // declared later than those declared in the base struct" (21.13.1.1).
        collectFields(superOf(s), fields, seen);

        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=s->getChildren().begin();
            it!=s->getChildren().end(); it++) {
            ast::IField *f = dynamic_cast<ast::IField *>(it->get());
            if (f && (f->getAttr() & ast::FieldAttr::Static)
                    == ast::FieldAttr::NoFlags) {
                fields.push_back(f);
            }
        }
    }

    static PackableInfo notACollection(const char *what) {
        return PackableInfo::notPackable(what, 0,
            "use a fixed-size array, 'T name[N]'");
    }

    static const char *kindName(ast::StructKind k) {
        switch (k) {
            case ast::StructKind::Buffer:   return "buffer";
            case ast::StructKind::Resource: return "resource";
            case ast::StructKind::Stream:   return "stream";
            case ast::StructKind::State:    return "state";
            default:                        return "struct";
        }
    }

private:
    dmgr::IDebug                        *m_dbg;
    IFactory                            *m_factory;
    ast::ISymbolScope                   *m_root;
    TaskResolveSymbolPathRef            m_resolver;
    PackableInfo                        m_info;
    std::set<ast::ISymbolTypeScope *>   m_active;
    std::set<ast::IScopeChild *>        m_bound;

};

} /* namespace pssp */
