/*
 * ScopeUtil.h
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#pragma once
#include "ExprId.h"
#include "NamedScopeChild.h"
#include "Scope.h"
#include "ScopeChild.h"

namespace pssp {

class ScopeUtil {
public:
	ScopeUtil();

	virtual ~ScopeUtil();

	static NamedScopeChild *findChild(Scope *s, const std::string &name);

	static bool addChild(Scope *s, NamedScopeChild *c);

	static void addChild(Scope *s, ScopeChild *c);
};

} /* namespace pssp */

