/*
 * Formatter.cpp
 *
 *  Created on: Sep 26, 2020
 *      Author: ballance
 */

#include "Formatter.h"
#include "PSSLexer.h"
#include "PSSParser.h"

using namespace antlr4;

Formatter::Formatter() {
	// TODO Auto-generated constructor stub

}

Formatter::~Formatter() {
	// TODO Auto-generated destructor stub
}

void Formatter::format(
			std::istream	*in,
			std::ostream	*out) {
    std::ifstream stream;
    stream.open("input.scene");

    ANTLRInputStream input(*in);
    PSSLexer lexer(&input);
    CommonTokenStream tokens(&lexer);
    PSSParser parser(&tokens);
    parser.addParseListener(this);
    parser.compilation_unit();
}

void Formatter::visitTerminal(antlr4::tree::TerminalNode *node) {
	fprintf(stdout, "visitTerminal: %s\n", node->getText().c_str());

}

void Formatter::visitErrorNode(antlr4::tree::ErrorNode *node) {
	fprintf(stdout, "visitErrorNode: %s\n", node->getText().c_str());
}

