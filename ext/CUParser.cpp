/*
 * CUParser.cpp
 *
 *  Created on: Apr 30, 2020
 *      Author: ballance
 */

#include "CUParser.h"

CUParser::CUParser() {
	// TODO Auto-generated constructor stub

}

CUParser::~CUParser() {
	// TODO Auto-generated destructor stub
}

antlrcpp::Any CUParser::visitAction_declaration(PSSParser::Action_declarationContext *context) {
	context->action_identifier()->accept(this);
}

