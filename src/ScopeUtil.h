/*
 * ScopeUtil.h
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#pragma once
#include "ExprId.h"
#include "pssp/ast/INamedScopeChild.h"
#include "pssp/ast/IScope.h"
#include "pssp/ast/IScopeChild.h"

namespace pssp {

class ScopeUtil {
public:
	ScopeUtil();

	virtual ~ScopeUtil();

	static ast::INamedScopeChild *findChild(ast::IScope *s, const std::string &name);

	static bool addChild(ast::IScope *s, ast::INamedScopeChild *c);

	static void addChild(ast::IScope *s, ast::IScopeChild *c);
};

} /* namespace pssp */

