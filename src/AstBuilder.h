/*
 * AstBuilder.h
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <iostream>
#include "pssp/ast/IGlobalScope.h"
#include "pssp/IMarkerListener.h"

namespace pssp {

class AstBuilderInt;
typedef std::unique_ptr<AstBuilderInt> AstBuilderIntUP;

class AstBuilder {
public:
	AstBuilder(IMarkerListener *marker_l);

	virtual ~AstBuilder();

	void build(
			ast::IGlobalScope	*global,
			std::istream		*in);

private:
	AstBuilderIntUP				m_builder_int;
};

} /* namespace pssp */

