/*
 * AssocDataTypeScopeSizeof.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
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
#include "pssp/impl/TaskGetTemplateParamDeclDefault.h"
#include "pssp/impl/TaskClassifyPackable.h"
#include "AssocDataTypeScopeSizeof.h"


namespace pssp {



AssocDataTypeScopeSizeof::AssocDataTypeScopeSizeof() {

}

AssocDataTypeScopeSizeof::~AssocDataTypeScopeSizeof() {

}

void AssocDataTypeScopeSizeof::postSpecialize(
        ResolveContext          *ctxt,
        ast::ITypeScope         *type) {
    DEBUG_INIT("pssp::AssocDataTypeScopeSizeof", ctxt->getDebugMgr());
    DEBUG_ENTER("postSpecialize");

    std::pair<ast::IDataType *, ast::IExpr *> val = 
        TaskGetTemplateParamDeclDefault(ctxt->getDebugMgr()).default_val(
            type->getParams()->getParams().at(0).get());

    if (!val.first) {
        DEBUG_ERROR("sizeof_s parameter lacking default");
        return;
    }

    // Size now if we can. A member type that is not bound yet -- the argument
    // is declared after this use, or is a specialization whose body has not
    // been resolved -- makes the answer Incomplete rather than wrong; try
    // again once resolution is finished.
    if (!setSize(ctxt, type, val.first)) {
        ast::IDataType *arg = val.first;
        ctxt->addPostResolveAction([ctxt, type, arg]() {
            setSize(ctxt, type, arg);
        });
    }

    DEBUG_LEAVE("postSpecialize");
}

bool AssocDataTypeScopeSizeof::setSize(
        ResolveContext          *ctxt,
        ast::ITypeScope         *type,
        ast::IDataType          *arg) {
    PackableInfo info = TaskClassifyPackable(
        ctxt->getFactory(),
        ctxt->root()).classify(arg);

    // A type with no packed size -- not packable (21.13.2.1), or not known --
    // gets no value. The declared placeholder stays, rather than a made-up
    // number that would silently size a register.
    if (info.kind != PackableInfo::Ok) {
        return (info.kind == PackableInfo::NotPackable);
    }

    int64_t nbits = info.bits;
    // 21.13.2.2: nbytes rounds up -- sizeof_s<bit[33]>::nbytes == 5.
    int64_t nbytes = (nbits + 7) / 8;

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=type->getChildren().begin();
        it!=type->getChildren().end(); it++) {
        ast::IField *f = dynamic_cast<ast::IField *>(it->get());
        if (!f) {
            continue;
        }
        int64_t v;
        if (f->getName()->getId() == "nbytes") {
            v = nbytes;
        } else if (f->getName()->getId() == "nbits") {
            v = nbits;
        } else {
            continue;
        }
        char tmp[32];
        snprintf(tmp, sizeof(tmp), "%lld", (long long)v);
        f->setInit(ctxt->getFactory()->getAstFactory()->mkExprSignedNumber(
            tmp,
            32,
            v));
    }
    return true;
}

dmgr::IDebug *AssocDataTypeScopeSizeof::m_dbg = 0;

}
