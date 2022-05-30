/*
 * RefExprUtil.h
 *
 *  Created on: Oct 30, 2020
 *      Author: ballance
 */

#include "pssp/ast/IRefExpr.h"
#include "pssp/ast/IRefExprTypeScopeGlobal.h"
#include "pssp/ast/IRefExprTypeScopeContext.h"
#include "pssp/ast/IRefExprScopeIndex.h"

namespace pssp {

class RefExprUtil {
public:
	RefExprUtil();

	virtual ~RefExprUtil();

	static ast::IRefExprTypeScopeGlobalSP mkTypeScopeGlobal(int32_t fileid);

	static ast::IRefExprScopeIndexSP mkScopeIndex(ast::IRefExprSP base, int32_t index);
};

} /* namespace pssp */

