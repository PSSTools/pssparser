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
#include "pssp/impl/TaskComputeTypePackedSize.h"
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

    // Need to calculate bit-width of 
    int32_t bits = TaskComputeTypePackedSize(
        ctxt->getFactory(),
        ctxt->root()).bits(val.first);
    DEBUG("bits: %d", bits);

    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=type->getChildren().begin();
        it!=type->getChildren().end(); it++) {
        ast::IScopeChild *c = it->get();
        ast::IField *f;
        if ((f=dynamic_cast<ast::IField *>(c))) {
            char tmp[16];
            if (f->getName()->getId() == "nbytes") {
                DEBUG("Setting nbytes");
                snprintf(tmp, sizeof(tmp), "%d", bits/8);
                f->setInit(ctxt->getFactory()->getAstFactory()->mkExprSignedNumber(
                    tmp,
                    32,
                    bits/8));
            } else if (f->getName()->getId() == "nbits") {
                DEBUG("Setting nbits");
                snprintf(tmp, sizeof(tmp), "%d", bits);
                f->setInit(ctxt->getFactory()->getAstFactory()->mkExprSignedNumber(
                    tmp,
                    32,
                    bits));
            }
        }
    }

    DEBUG_LEAVE("postSpecialize");
}

dmgr::IDebug *AssocDataTypeScopeSizeof::m_dbg = 0;

}
