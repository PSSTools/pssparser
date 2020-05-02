/*
 * CUParser.h
 *
 *  Created on: Apr 30, 2020
 *      Author: ballance
 */

#ifndef CUPARSER_H_
#define CUPARSER_H_
#include "antlr4-runtime.h"
#include "PSSVisitor.h"

using namespace antlrcpp;

class CUParser : public PSSVisitor {
public:
	CUParser();

	virtual ~CUParser();

	/****************************************************************
	 * B02 Action
	 ****************************************************************/

    virtual antlrcpp::Any visitAction_declaration(PSSParser::Action_declarationContext *context);

};

#endif /* CUPARSER_H_ */
