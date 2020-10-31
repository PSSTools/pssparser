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

RefExprTypeScopeGlobalSP RefExprUtil::mkTypeScopeGlobal(int32_t fileid) {
	return RefExprTypeScopeGlobalSP(new RefExprTypeScopeGlobal(fileid));
}

RefExprScopeIndexSP RefExprUtil::mkScopeIndex(RefExprSP base, int32_t index) {
	return RefExprScopeIndexSP(new RefExprScopeIndex(base, index));
}

} /* namespace pssp */
