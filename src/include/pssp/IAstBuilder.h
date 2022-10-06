/*
 * IAstBuilder.h
 *
 *  Created on: May 27, 2022
 *      Author: mballance
 */

#pragma once
#include <iostream>
#include "pssp/ast/IGlobalScope.h"
#include "pssp/IMarkerListener.h"


namespace pssp {

class IAstBuilder {
public:

	virtual ~IAstBuilder() { }

	virtual void build(
		ast::IGlobalScope		*global,
		std::istream			*in,
		IMarkerListener			*marker_l) = 0;

};

}
