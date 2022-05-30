/*
 * AstBuilder.cpp
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#include <stdio.h>
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
		ast::IGlobalScope	*global,
		std::istream		*in) {
	fprintf(stdout, "AstBuilder::build: this=%p\n", this);
	fprintf(stdout, "AstBuilder::build: global=%p %p\n", global, dynamic_cast<ast::IGlobalScope *>(global));
	fprintf(stdout, "AstBuilder::build: in=%p %p\n", in, dynamic_cast<std::istream *>(in));
	m_builder_int->build(global, in);
}

} /* namespace pssp */
