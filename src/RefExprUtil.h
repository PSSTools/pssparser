/*
 * RefExprUtil.h
 *
 *  Created on: Oct 30, 2020
 *      Author: ballance
 */

#include "RefExpr.h"
#include "RefExprTypeScopeGlobal.h"
#include "RefExprTypeScopeContext.h"
#include "RefExprScopeIndex.h"

namespace pssp {

class RefExprUtil {
public:
	RefExprUtil();

	virtual ~RefExprUtil();

	static RefExprTypeScopeGlobalSP mkTypeScopeGlobal(int32_t fileid);

	static RefExprScopeIndexSP mkScopeIndex(RefExprSP base, int32_t index);
};

} /* namespace pssp */

