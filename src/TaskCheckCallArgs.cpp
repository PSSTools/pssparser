/**
 * TaskCheckCallArgs.cpp
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
#include "pssp/ast/IFunctionDefinition.h"
#include "pssp/ast/IFunctionImportProto.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IFunctionParamDecl.h"
#include "pssp/ast/IMethodParameterList.h"
#include "pssp/ast/IProceduralStmtDataDeclaration.h"
#include "pssp/ast/ISymbolFunctionScope.h"
#include "TaskCheckCallArgs.h"
#include "TaskExprTypeCat.h"


namespace pssp {

dmgr::IDebug *TaskCheckCallArgs::m_dbg = 0;

TaskCheckCallArgs::TaskCheckCallArgs(ResolveContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("pssp::TaskCheckCallArgs", ctxt->getDebugMgr());
}

TaskCheckCallArgs::~TaskCheckCallArgs() {

}

void TaskCheckCallArgs::check(
    ast::IScopeChild            *target,
    ast::IExprMemberPathElem    *elem) {
    DEBUG_ENTER("check");

    if (!target || !elem || !elem->getParams()) {
        DEBUG_LEAVE("check -- not a call");
        return;
    }

    std::vector<ast::IFunctionPrototype *> protos;
    collectPrototypes(target, protos);

    if (protos.empty()) {
        // Nothing with a signature. Either the target is a value -- which is
        // never callable and is reported -- or it is something the resolver
        // models loosely, in which case staying silent beats guessing.
        if (const char *what = valueKind(target)) {
            m_ctxt->addErrorMarker(
                elem->getId()->getLocation(),
                "'%s' is not a function; it is %s",
                elem->getId()->getId().c_str(),
                what);
            DEBUG_LEAVE("check -- not a function");
        } else {
            DEBUG_LEAVE("check -- no signature");
        }
        return;
    }

    int32_t n_args = elem->getParams()->getParameters().size();
    const std::string &name = elem->getId()->getId();

    // A single accepting candidate is enough.
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=protos.begin(); it!=protos.end(); it++) {
        int32_t min, max;
        arity(*it, min, max);
        if (n_args >= min && (max < 0 || n_args <= max)) {
            if (protos.size() == 1) {
                // With an overload set there is no single parameter list to
                // compare against, and picking one would mean implementing
                // overload resolution.
                checkArgTypes(*it, elem);
            }
            DEBUG_LEAVE("check -- %s accepts %d args", name.c_str(), n_args);
            return;
        }
    }

    if (protos.size() == 1) {
        int32_t min, max;
        arity(protos.at(0), min, max);
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "call to '%s' %s, got %d",
            name.c_str(),
            expectation(min, max).c_str(),
            n_args);
    } else {
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "no overload of '%s' accepts %d argument%s",
            name.c_str(),
            n_args,
            (n_args == 1)?"":"s");
    }

    DEBUG_LEAVE("check -- reported");
}

void TaskCheckCallArgs::collectPrototypes(
    ast::IScopeChild                            *target,
    std::vector<ast::IFunctionPrototype *>      &protos) {
    ast::ISymbolFunctionScope *fs =
        dynamic_cast<ast::ISymbolFunctionScope *>(target);

    if (fs) {
        // Prototypes, the definition, and imports all describe the same
        // function name, and a redeclaration repeats the signature rather than
        // adding an overload. Duplicates would only weaken the check, so they
        // are filtered by identity.
        for (std::vector<ast::IFunctionPrototype *>::const_iterator
            it=fs->getPrototypes().begin();
            it!=fs->getPrototypes().end(); it++) {
            protos.push_back(*it);
        }

        if (fs->getDefinition() && fs->getDefinition()->getProto()) {
            protos.push_back(fs->getDefinition()->getProto());
        }

        for (std::vector<ast::IFunctionImportUP>::const_iterator
            it=fs->getImport_specs().begin();
            it!=fs->getImport_specs().end(); it++) {
            ast::IFunctionImportProto *ip =
                dynamic_cast<ast::IFunctionImportProto *>(it->get());
            if (ip && ip->getProto()) {
                protos.push_back(ip->getProto());
            }
        }
    } else if (ast::IFunctionDefinition *fd =
        dynamic_cast<ast::IFunctionDefinition *>(target)) {
        if (fd->getProto()) {
            protos.push_back(fd->getProto());
        }
    } else if (ast::IFunctionPrototype *fp =
        dynamic_cast<ast::IFunctionPrototype *>(target)) {
        protos.push_back(fp);
    }

    // Collapse signatures that are arity-equivalent, so that a function
    // declared once and defined once is not reported as an overload set.
    std::vector<ast::IFunctionPrototype *> unique;
    for (std::vector<ast::IFunctionPrototype *>::const_iterator
        it=protos.begin(); it!=protos.end(); it++) {
        int32_t min, max;
        arity(*it, min, max);
        bool dup = false;
        for (std::vector<ast::IFunctionPrototype *>::const_iterator
            uit=unique.begin(); uit!=unique.end(); uit++) {
            int32_t u_min, u_max;
            arity(*uit, u_min, u_max);
            if (u_min == min && u_max == max) {
                dup = true;
                break;
            }
        }
        if (!dup) {
            unique.push_back(*it);
        }
    }
    protos = unique;
}

void TaskCheckCallArgs::arity(
    ast::IFunctionPrototype     *proto,
    int32_t                     &min,
    int32_t                     &max) {
    min = 0;
    max = 0;

    for (std::vector<ast::IFunctionParamDeclUP>::const_iterator
        it=proto->getParameters().begin();
        it!=proto->getParameters().end(); it++) {
        if ((*it)->getIs_varargs()) {
            // A varargs parameter soaks up everything that follows, and
            // supplies nothing itself.
            max = -1;
            return;
        }
        if (!(*it)->getDflt()) {
            min++;
        }
        max++;
    }
}

std::string TaskCheckCallArgs::expectation(int32_t min, int32_t max) {
    char tmp[128];

    if (max < 0) {
        // min == 0 is unreachable here: a purely variadic signature accepts
        // every count, so the caller never gets as far as reporting.
        snprintf(tmp, sizeof(tmp), "expects at least %d argument%s",
            min, (min == 1)?"":"s");
    } else if (min == max) {
        snprintf(tmp, sizeof(tmp), "expects %d argument%s",
            min, (min == 1)?"":"s");
    } else {
        snprintf(tmp, sizeof(tmp), "expects %d to %d arguments", min, max);
    }

    return tmp;
}

const char *TaskCheckCallArgs::valueKind(ast::IScopeChild *target) {
    // Only declarations that are unambiguously *values* are named here. A
    // type, a scope, or anything the resolver models loosely is left out on
    // purpose: this must not fire on a construct the linker merely models
    // badly, and the set of things `TaskResolveSymbolPathRef` can hand back is
    // wider than the set of things this pass understands.
    if (dynamic_cast<ast::IFunctionParamDecl *>(target)) {
        return "a parameter";
    } else if (dynamic_cast<ast::IProceduralStmtDataDeclaration *>(target)) {
        return "a variable";
    } else if (dynamic_cast<ast::IField *>(target)) {
        return "a field";
    }

    return 0;
}

void TaskCheckCallArgs::checkArgTypes(
    ast::IFunctionPrototype     *proto,
    ast::IExprMemberPathElem    *elem) {
    DEBUG_ENTER("checkArgTypes");

    const std::vector<ast::IFunctionParamDeclUP> &params = proto->getParameters();
    const std::vector<ast::IExprUP> &args = elem->getParams()->getParameters();
    TaskExprTypeCat cat(m_ctxt);

    for (uint32_t ii=0; ii<args.size(); ii++) {
        // Arguments past the fixed parameters land on the varargs parameter,
        // which is always last and carries the element type.
        ast::IFunctionParamDecl *param = 0;
        if (ii < params.size()) {
            param = params.at(ii).get();
        } else if (params.size() && params.back()->getIs_varargs()) {
            param = params.back().get();
        }

        if (!param || !param->getType()) {
            continue;
        }
        if (param->getKind() != ast::FunctionParamDeclKind::ParamKind_DataType) {
            // Type parameters and `ref` parameters name a type rather than
            // describe a value; neither is a category comparison.
            continue;
        }

        TypeCatE decl_c = cat.dataType(param->getType());
        if (decl_c == TypeCatE::Unknown) {
            continue;
        }

        TypeCatE arg_c = cat.expr(args.at(ii).get());
        if (TaskExprTypeCat::compatible(decl_c, arg_c)) {
            continue;
        }

        // `IExpr` carries no source location, so the call site is the best
        // anchor available; the argument index in the message makes up for it.
        m_ctxt->addErrorMarker(
            elem->getId()->getLocation(),
            "argument %d to '%s' expects %s, got %s",
            ii+1,
            elem->getId()->getId().c_str(),
            TaskExprTypeCat::dataTypeName(param->getType(), decl_c),
            TaskExprTypeCat::name(arg_c));
    }

    DEBUG_LEAVE("checkArgTypes");
}

}
