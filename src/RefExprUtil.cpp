/*
 * RefExprUtil.cpp
 *
 *  Created on: Oct 30, 2020
 *      Author: ballance
 */

#include "RefExprUtil.h"

namespace pssp {

RefExprUtil::RefExprUtil() {
	// TODO Auto-generated constructor stub

}

RefExprUtil::~RefExprUtil() {
	// TODO Auto-generated destructor stub
}

ast::IRefExprTypeScopeGlobalSP RefExprUtil::mkTypeScopeGlobal(int32_t fileid) {
	/*
	return ast::IRefExprTypeScopeGlobalSP(new ast::IRefExprTypeScopeGlobal(fileid));
	 */
	return ast::IRefExprTypeScopeGlobalSP(0);
}

ast::IRefExprScopeIndexSP RefExprUtil::mkScopeIndex(ast::IRefExprSP base, int32_t index) {
//	return ast::IRefExprScopeIndexSP(new ast::IRefExprScopeIndex(base, index));
	return ast::IRefExprScopeIndexSP(0);
}

} /* namespace pssp */
