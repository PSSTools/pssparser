/*
 * Formatter.h
 *
 *  Created on: Sep 26, 2020
 *      Author: ballance
 */

#pragma once
#include "PSSBaseListener.h"
#include <iostream>

class Formatter : public PSSBaseListener {
public:
	Formatter();

	virtual ~Formatter();

	void format(
			std::istream	*in,
			std::ostream	*out);

	virtual void visitTerminal(antlr4::tree::TerminalNode *node) override;

	virtual void visitErrorNode(antlr4::tree::ErrorNode *node) override;

};

