/*
 * AstBuilder.cpp
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#include "AstBuilder.h"

#include "AstBuilderInt.h"

namespace pssp {

AstBuilder::AstBuilder(IMarkerListener *marker_l) :
	m_builder_int(new AstBuilderInt(marker_l)) {
	// TODO Auto-generated constructor stub

}

AstBuilder::~AstBuilder() {
	// TODO Auto-generated destructor stub
}

void AstBuilder::build(
		GlobalScope			*global,
		std::istream		*in) {
	m_builder_int->build(global, in);
}

} /* namespace pssp */
